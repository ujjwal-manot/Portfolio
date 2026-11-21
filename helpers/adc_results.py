# Reads the ADC's ngspice results and checks them against chip.md: comparator decisions (right sign for every input beyond 50 uV, well past the measured hysteresis, and done inside the 50 ns half clock), Monte Carlo offset and hysteresis spread, DAC level errors as DNL and INL (limits +-0.5 and +-1 LSB, endpoint fit), and a co-simulated conversion (which must hold the full record of a tone coherent to 0.001 bin, measured from the simulated input) as ENOB from a coherent FFT (limit 7.5 bits), offset and gain from the tone, and power: python3 adc_results.py decide|offset|levels|convert ...
import math, statistics, sys
import numpy as np
from adc_spectrum import spectrum, coherent_bin

LSB = 0.8 / 256
SIGN_FROM, BUDGET = 50e-6, 50e-9
LIMITS = {"dnl": 0.5, "inl": 1.0, "enob": 7.5}

def decisions(paths, supply):
    problems, worst = [], {}
    for path in paths:
        for line in open(path).readlines()[1:]:
            parts = line.split()
            dv, t, high = float(parts[0]), parts[1] if len(parts) == 3 else "", float(parts[-1]) > supply / 2
            if abs(dv) >= SIGN_FROM and high != (dv > 0):
                problems.append(f"{path}: {dv:g} V decided {'high' if high else 'low'}")
            if t and float(t) > BUDGET:
                problems.append(f"{path}: {dv:g} V took {float(t):.3g} s")
            if t:
                worst[str(path)] = max(worst.get(str(path), 0), float(t))
    return {"problems": problems, "worst_s": worst}

def offsets(paths):
    rows = [dict(zip(*[iter(open(p).read().split())] * 2)) for p in paths]
    off = [float(r["offset_v"]) for r in rows]
    hyst = [float(r["hysteresis_v"]) for r in rows]
    return {"mean_v": statistics.mean(off), "sigma_v": statistics.stdev(off), "worst_v": max(off, key=abs), "hysteresis_max_v": max(hyst), "runs": len(off)}

def linearity(path):
    e = [float(l.split()[1]) for l in open(path).readlines()[1:]]
    dnl = [(e[d] - e[d - 1]) / LSB for d in range(1, len(e))]
    inl = [(e[d] - e[0] - (e[-1] - e[0]) * d / (len(e) - 1)) / LSB for d in range(len(e))]
    return {"dnl_min": min(dnl), "dnl_max": max(dnl), "inl_min": min(inl), "inl_max": max(inl)}

def codes_from_run(path, supply):
    rows = [[float(v) for v in l.split()][1::2] for l in open(path) if l.strip()]
    return [sum(1 << (7 - j) for j in range(8) if rows[i][1 + j] > supply / 2) for i in range(1, len(rows)) if rows[i][0] > supply / 2 >= rows[i - 1][0]]

def check_conversion(codes_path, measure_path, supply, n, fs=1e6):
    m = dict(zip(*[iter(open(measure_path).read().split())] * 2))
    codes, problems = codes_from_run(codes_path, supply)[2:], []
    if len(codes) < n:
        return {"problems": [f"{codes_path}: {len(codes)} codes, the record needs {n}"]}
    codes = codes[:n]
    try:
        k = coherent_bin(fs, n, float(m["fin_hz"]), tolerance=1e-3)
    except ValueError as e:
        return {"problems": [f"{codes_path}: {e}"]}
    r = spectrum(codes, k)
    x = np.asarray(codes, float)
    amplitude = 2 * abs(np.sum(x * np.exp(-2j * np.pi * k * np.arange(n) / n))) / n
    r.update(offset_lsb=x.mean() - 127.5, gain=amplitude / (0.4 * 10 ** (-0.5 / 20) / LSB), power_w=sum(abs(float(m[q])) for q in ("p_vdd_w", "p_hi_w", "p_lo_w", "p_cm_w")))
    if r["enob"] < LIMITS["enob"]:
        problems.append(f"{codes_path}: enob below {LIMITS['enob']}")
    r["problems"] = problems
    return r

if __name__ == "__main__":
    mode, args, fails = sys.argv[1], sys.argv[2:], []
    if mode == "decide":
        r = decisions(args[1:], float(args[0]))
        for path, t in r["worst_s"].items():
            print(f"{path}: slowest decision {t:.4g} s")
        fails = r["problems"]
    elif mode == "offset":
        r = offsets(args)
        print(f"offset mean {r['mean_v']:.4g} V sigma {r['sigma_v']:.4g} V worst {r['worst_v']:.4g} V ({r['worst_v'] / LSB:.3g} LSB), hysteresis worst {r['hysteresis_max_v']:.4g} V over {r['runs']} runs")
    elif mode == "levels":
        for path in args:
            r = linearity(path)
            print(f"{path}: dnl {r['dnl_min']:.3f} to {r['dnl_max']:.3f} LSB, inl {r['inl_min']:.3f} to {r['inl_max']:.3f} LSB")
            fails += [f"{path}: {k} beyond +-{LIMITS[k]} LSB" for k in ("dnl", "inl") if max(-r[f"{k}_min"], r[f"{k}_max"]) > LIMITS[k]]
    elif mode == "convert":
        supply, n, path, measure = float(args[0]), int(args[1]), args[2], args[3]
        r = check_conversion(path, measure, supply, n)
        if "enob" in r:
            print(f"{path}: {n} codes, enob {r['enob']:.3f} bits, sndr {r['sndr_db']:.2f} dB, sfdr {r['sfdr_db']:.2f} dB, offset {r['offset_lsb']:.2f} LSB, gain {r['gain']:.4f}, power {r['power_w']:.4g} W")
        fails = r["problems"]
    for f in fails:
        print("FAIL " + f)
    print("every check passes" if not fails else f"{len(fails)} failures")
    sys.exit(1 if fails else 0)
