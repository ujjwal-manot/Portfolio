# Reads the ADC's supply and noise results: current gives the 1.2 V supply's average current over the conversions after calibration (from measure.txt), the references' currents, the calibration-phase average and the highest 50 ns average (from the energy integral in convert.txt, so spikes shorter than 50 ns are averaged away); wave reads a full-resolution supply current record (time, current) and gives its peak, its average over the conversions and the charge drawn in each half clock period (each clk edge); refs gives how far vref_hi minus vref_lo, vcm and the pair's mid point move at the comparator decisions (each comp_clk rise, read between solver steps) from their median, in LSB; ktc gives the sampled kT/C noise in LSB and what it costs an ideal 8-bit quantizer's ENOB, failing above 0.0774 LSB rms (a 0.05 bit ENOB loss, the budget fixed before the runs) or outside 0.5 to 2 times sqrt(kT/2.05 pF) at the corner's temperature (the bench would be wrong); fom gives the Walden and Schreier figures of merit from a conversion and the SAR logic's power report: python3 adc_supply.py current|wave|refs|ktc|fom ...
import math, statistics, sys
from adc_results import check_conversion, LSB
from adc_histogram import walden, schreier

CAL_END, CLK_HALF, FS = 9.3e-6, 50e-9, 1e6
KTC_LIMIT = 0.0774

def rows(path):
    out = [[float(v) for v in l.split()] for l in open(path) if l.strip()]
    if not out or any(math.isnan(v) for r in out for v in r):
        raise ValueError(f"{path}: empty or holds nan")
    return out

def measure(path):
    m = {k: float(v) for k, v in zip(*[iter(open(path).read().split())] * 2)}
    for key in ("p_vdd_w", "p_hi_w", "p_lo_w", "p_cm_w", "fin_hz"):
        if key not in m or not math.isfinite(m[key]):
            raise ValueError(f"{path}: {key} missing or not a number")
    return m

def current(supply, convert_path, measure_path):
    m, data = measure(measure_path), [r[1::2] for r in rows(convert_path)]
    t = [r[0] for r in rows(convert_path)]
    e = [r[13] for r in data]
    late = [(t[i], (e[i + 1] - e[i]) / (t[i + 1] - t[i]) / supply) for i in range(len(t) - 1) if t[i] >= CAL_END]
    cal = [i for i in range(len(t)) if 0.3e-6 <= t[i] <= 8.3e-6]
    return {"i_vdd_a": m["p_vdd_w"] / supply, "i_hi_a": m["p_hi_w"] / 1.0, "i_lo_a": m["p_lo_w"] / 0.2, "i_cm_a": m["p_cm_w"] / 0.6,
            "i_cal_a": (e[cal[-1]] - e[cal[0]]) / (t[cal[-1]] - t[cal[0]]) / supply, "peak_50ns_a": max(i for _, i in late),
            "charge_per_conversion_c": m["p_vdd_w"] / supply / FS}

def wave(path, end):
    data = rows(path)
    if data[-1][0] < end * (1 - 1e-6):
        raise ValueError(f"{path}: ends at {data[-1][0]:.4g} s, the run should reach {end:.4g} s")
    t, i = [r[0] for r in data], [r[1] for r in data]
    edges = []
    k = int(CAL_END / CLK_HALF)
    while (k + 1) * CLK_HALF <= t[-1]:
        a, b = k * CLK_HALF, (k + 1) * CLK_HALF
        q = sum((t[j + 1] - t[j]) * (i[j] + i[j + 1]) / 2 for j in range(len(t) - 1) if a <= t[j] < b)
        edges.append(q)
        k += 1
    late = [j for j in range(len(t)) if t[j] >= CAL_END]
    peak = max(late, key=lambda j: i[j])
    span = t[late[-1]] - t[late[0]]
    return {"peak_a": i[peak], "peak_t": t[peak], "average_a": sum(edges) / span, "edge_charge_max_c": max(edges), "edge_charge_mean_c": statistics.mean(edges), "edges": len(edges)}

def at_decisions(path, supply, columns):
    data = rows(path)
    out = []
    for a, b in zip(data, data[1:]):
        if a[1] < supply / 2 <= b[1]:
            f = (supply / 2 - a[1]) / (b[1] - a[1])
            out.append([a[c] + f * (b[c] - a[c]) for c in columns])
    if not out:
        raise ValueError(f"{path}: no comparator clock rise")
    return out

def refs(path, supply):
    points = at_decisions(path, supply, (3, 5, 7))
    series = {"vref_hi - vref_lo": [h - l for h, c, l in points], "vcm": [c for h, c, l in points], "pair mid point": [(h + l) / 2 for h, c, l in points]}
    return {k: (max(abs(v - statistics.median(s)) for v in s) / LSB, statistics.median(s)) for k, s in series.items()} | {"decisions": len(points)}

if __name__ == "__main__":
    mode, args, fails = sys.argv[1], sys.argv[2:], []
    if mode == "current":
        r = current(float(args[0]), args[1], args[2])
        print(f"{args[1]}: supply current {r['i_vdd_a'] * 1e6:.4g} uA average over the conversions, {r['charge_per_conversion_c'] * 1e12:.4g} pC per conversion, highest 50 ns average {r['peak_50ns_a'] * 1e6:.4g} uA, {r['i_cal_a'] * 1e6:.4g} uA during calibration")
        print(f"{args[1]}: reference currents vref_hi {r['i_hi_a'] * 1e6:.4g} uA, vref_lo {r['i_lo_a'] * 1e6:.4g} uA, vcm {r['i_cm_a'] * 1e6:.4g} uA (positive means drawn from the source)")
    elif mode == "wave":
        end = float(args[0])
        for path in args[1:]:
            r = wave(path, end)
            print(f"{path}: supply current peak {r['peak_a'] * 1e3:.4g} mA at {r['peak_t'] * 1e6:.4g} us, average {r['average_a'] * 1e6:.4g} uA after calibration, charge per clk edge {r['edge_charge_mean_c'] * 1e15:.4g} fC mean and {r['edge_charge_max_c'] * 1e15:.4g} fC most over {r['edges']} half periods")
    elif mode == "refs":
        supply = float(args[0])
        for path in args[1:]:
            r = refs(path, supply)
            for k in ("vref_hi - vref_lo", "vcm", "pair mid point"):
                print(f"{path}: {k} moves at most {r[k][0]:.4g} LSB from its median {r[k][1]:.5g} V over {r['decisions']} comparator decisions")
    elif mode == "ktc":
        v = float(dict(zip(*[iter(open(args[0]).read().split())] * 2))["ktc_rms_v"])
        anchor = math.sqrt(1.380649e-23 * (float(args[1]) + 273.15) / 2.05e-12)
        if not math.isfinite(v) or v <= 0:
            fails.append(f"{args[0]}: ktc_rms_v {v} is not a positive number")
        else:
            cost = 0.5 * math.log2(1 + (v / LSB) ** 2 * 12)
            print(f"{args[0]}: sampled kT/C noise {v * 1e6:.4g} uV rms, {v / LSB:.4g} LSB (limit {KTC_LIMIT} LSB), {v / anchor:.3g} times sqrt(kT/2.05 pF) at {args[1]} C; against 0.2887 LSB of quantization noise it costs an ideal 8-bit quantizer {cost:.4g} bits of ENOB")
            if v / LSB > KTC_LIMIT:
                fails.append(f"{args[0]}: kT/C noise {v / LSB:.4g} LSB, above {KTC_LIMIT} LSB")
            if not 0.5 <= v / anchor <= 2:
                fails.append(f"{args[0]}: kT/C noise is {v / anchor:.3g} times sqrt(kT/2.05 pF), outside 0.5 to 2, so the bench is wrong")
    elif mode == "fom":
        supply, n = float(args[0]), int(args[1])
        r = check_conversion(args[2], args[3], supply, n)
        logic = next(float(l.split()[4]) for l in open(args[4]) if l.startswith("Total"))
        p = r["power_w"] + logic
        print(f"{args[2]}: enob {r['enob']:.3f} bits, sndr {r['sndr_db']:.2f} dB at a {float(measure(args[3])['fin_hz']) / 1e3:.4g} kHz tone (not Nyquist), analog power {r['power_w'] * 1e6:.4g} uW, SAR logic {logic * 1e6:.4g} uW, total {p * 1e6:.4g} uW")
        print(f"{args[2]}: Walden figure of merit {walden(p, r['enob'], FS) * 1e15:.4g} fJ per conversion step, Schreier figure of merit {schreier(r['sndr_db'], FS / 2, p):.4g} dB")
    for f in fails:
        print("FAIL " + f)
    print("every check passes" if not fails else f"{len(fails)} failures")
    sys.exit(1 if fails else 0)
