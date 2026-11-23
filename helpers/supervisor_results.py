# Reads power_manager's supervisor results: in detector mode each detector_<corner>.txt (vdd_cpu then 64 capture-latch voltages per line, from tests/detector.cir) must have all 10 points from 0.80 to 1.25 V, numeric, the code (reached taps, as the clock stretch RTL counts them) between 1 and 63 (not saturated), never falling as vdd_cpu rises, and at most one bubble per point; in supervisor mode each sup_<corner>_<ramp>.txt (wrdata pairs of vin, vdd_mem, vin_ok, mem_ok, rst_n, vref and the vin current, from tests/supervisor_bench.cir) must reach its end time, show exactly one comparator change in each test phase, keep vin's falling trip in [2.80, 3.00) V (the rated 3.0 to 3.6 V input never resets, and a 100 mV error either way leaves the window), its rising trip under 3.00 V (a supply at the rated minimum releases reset) with at least 20 mV of hysteresis, vdd_mem's falling trip in [1.08, 1.14] V (the SRAM macros' characterized floor, and the DLDO coarse window's low edge at 1.2 V) and its rising trip at or under 1.17 V (under the fine window's 1.188 V edge) with at least 10 mV of hysteresis, and hold rst_n low whenever vin is under 2.80 V or vdd_mem under 1.08 V, releasing it before the trip tests start; in mc mode the same checks per seed give the yield (pass at 99% or more) and its one-sided 95% lower bound: python3 supervisor_results.py detector|supervisor|mc files...
import math, re, statistics, sys
from pathlib import Path
from analog_results import lower_bound

NT, POINTS = 64, 10
VIN_FALL, VIN_RISE_MAX, VIN_HYST = (2.80, 3.00), 3.00, 0.020
MEM_FALL, MEM_RISE_MAX, MEM_HYST = (1.08, 1.14), 1.17, 0.010
YIELD = 0.99


def decode(volts, vmem=1.2):
    reached = [(v > vmem / 2) == (k % 2 == 0) for k, v in enumerate(volts, 1)]
    return sum(reached), sum(1 for a, b in zip(reached, reached[1:]) if b and not a)


def detector(paths):
    ok, lines = True, []
    for path in paths:
        name = re.sub(r"^.*detector_", "", Path(path).stem)
        rows = [[float(x) for x in l.split()] for l in Path(path).read_text().splitlines() if l.strip()]
        bad = [r for r in rows if len(r) != NT + 1 or any(math.isnan(x) for x in r)]
        if len(rows) != POINTS or bad:
            ok = False
            lines.append(f"detector {name}: {len(rows)} points of {POINTS}, {len(bad)} malformed: FAIL")
            continue
        codes = [(r[0], *decode(r[1:])) for r in rows]
        for v, c, b in codes:
            lines.append(f"detector {name} vdd_cpu {v:.3f} V code {c} bubbles {b}")
        problems = [f"code {c} at {v:.3f} V saturates" for v, c, _ in codes if not 1 <= c <= NT - 1]
        problems += [f"{b} bubbles at {v:.3f} V" for v, _, b in codes if b > 1]
        problems += [f"code falls from {a[1]} to {b[1]} between {a[0]:.3f} and {b[0]:.3f} V" for a, b in zip(codes, codes[1:]) if b[1] < a[1]]
        for setpoint in (0.9, 1.0, 1.1, 1.2):
            (v1, c1), (v2, c2) = [min(codes, key=lambda x: abs(x[0] - s))[:2] for s in (setpoint - 0.05, setpoint)]
            lines.append(f"detector {name} from {v1:.2f} to {v2:.2f} V: {(v2 - v1) * 1000 / max(c2 - c1, 1e-9):.1f} mV per code step")
        lines += [f"detector {name}: {p}" for p in problems]
        lines.append(f"detector {name}: {'FAIL' if problems else 'pass'}")
        ok = ok and not problems
    return ok, lines


def read_sup(path):
    rows = []
    for l in Path(path).read_text().splitlines():
        x = [float(v) for v in l.split()]
        rows.append([x[0]] + x[1::2])
    return rows


def crossings(rows, col, start, stop):
    out = []
    for a, b in zip(rows, rows[1:]):
        if start <= a[0] < stop:
            ha, hb = a[col] > a[1] / 2, b[col] > b[1] / 2
            if ha != hb:
                out.append((hb, a, b))
    return out


def level(a, b, col, edge_col):
    fa, fb = a[edge_col] - a[1] / 2, b[edge_col] - b[1] / 2
    w = fa / (fa - fb) if fa != fb else 0.0
    return a[col] + w * (b[col] - a[col])


def trips(rows, ramp):
    t0 = ramp + 150e-6
    phases = {"vin_fall": (3, 1, t0, t0 + 600e-6), "vin_rise": (3, 1, t0 + 600e-6, t0 + 1200e-6),
              "mem_fall": (4, 2, t0 + 1250e-6, t0 + 1750e-6), "mem_rise": (4, 2, t0 + 1750e-6, t0 + 2250e-6)}
    got = {}
    for name, (col, rail, start, stop) in phases.items():
        found = crossings(rows, col, start, stop)
        got[name] = level(found[0][1], found[0][2], rail, col) if len(found) == 1 and found[0][0] == name.endswith("rise") else float("nan")
        got[name + "_changes"] = len(found)
    return got


def check(path):
    ramp = float(re.search(r"_([0-9.]+)u$", Path(path).stem).group(1)) * 1e-6 if re.search(r"_([0-9.]+)u$", Path(path).stem) else 100e-6
    rows = read_sup(path)
    end = ramp + 150e-6 + 2300e-6
    if not rows or rows[-1][0] < end * (1 - 1e-6) or any(len(r) != 8 or any(math.isnan(x) for x in r) for r in rows):
        return {}, [f"run stopped at {rows[-1][0] if rows else 0:.4g} s of {end:.4g} s or has bad rows"]
    got = trips(rows, ramp)
    problems = [f"{k} changed {got[k + '_changes']} times, wants once" for k in ("vin_fall", "vin_rise", "mem_fall", "mem_rise") if got[k + "_changes"] != 1]
    vf, vr, mf, mr = got["vin_fall"], got["vin_rise"], got["mem_fall"], got["mem_rise"]
    if not VIN_FALL[0] <= vf < VIN_FALL[1]:
        problems.append(f"vin falling trip {vf:.4f} V outside [{VIN_FALL[0]:.2f}, {VIN_FALL[1]:.2f})")
    if not vr < VIN_RISE_MAX or not vr - vf >= VIN_HYST:
        problems.append(f"vin rising trip {vr:.4f} V, hysteresis {1000 * (vr - vf):.1f} mV (limits under {VIN_RISE_MAX:.2f} V, at least {1000 * VIN_HYST:.0f} mV)")
    if not MEM_FALL[0] <= mf <= MEM_FALL[1]:
        problems.append(f"vdd_mem falling trip {mf:.4f} V outside [{MEM_FALL[0]:.2f}, {MEM_FALL[1]:.2f}]")
    if not mr <= MEM_RISE_MAX or not mr - mf >= MEM_HYST:
        problems.append(f"vdd_mem rising trip {mr:.4f} V, hysteresis {1000 * (mr - mf):.1f} mV (limits at most {MEM_RISE_MAX:.2f} V, at least {1000 * MEM_HYST:.0f} mV)")
    early = [r for r in rows if (r[1] < VIN_FALL[0] or r[2] < MEM_FALL[0]) and r[5] > max(r[2] / 2, 0.1)]
    if early:
        problems.append(f"rst_n high at vin {early[0][1]:.3f} V, vdd_mem {early[0][2]:.3f} V (t = {early[0][0]:.4g} s)")
    released = [r for r in rows if r[5] > r[2] / 2 and r[2] > 0.5]
    t0 = ramp + 150e-6
    if not released or released[0][0] >= t0:
        problems.append("rst_n never released after power-up")
    else:
        got["release_vin"], got["release_mem"] = released[0][1], released[0][2]
    got["supply_a"] = -[r for r in rows if r[0] <= t0][-1][7]
    return got, problems


def fmt(got):
    keys = [("vin_fall", "vin falling trip", "V"), ("vin_rise", "vin rising trip", "V"), ("mem_fall", "vdd_mem falling trip", "V"), ("mem_rise", "vdd_mem rising trip", "V")]
    parts = [f"{label} {got[k]:.4f} {u}" for k, label, u in keys if k in got]
    if "vin_fall" in got:
        parts.append(f"vin hysteresis {1000 * (got['vin_rise'] - got['vin_fall']):.1f} mV")
        parts.append(f"vdd_mem hysteresis {1000 * (got['mem_rise'] - got['mem_fall']):.1f} mV")
    if "release_vin" in got:
        parts.append(f"reset released at vin {got['release_vin']:.3f} V vdd_mem {got['release_mem']:.3f} V")
    if "supply_a" in got:
        parts.append(f"bandgap and supervisor current {1e6 * got['supply_a']:.1f} uA")
    return ", ".join(parts)


def supervisor(paths):
    ok, lines = True, []
    for path in paths:
        got, problems = check(path)
        name = re.sub(r"^sup_", "", Path(path).stem)
        lines.append(f"supervisor {name}: {fmt(got)}")
        lines += [f"supervisor {name}: {p}" for p in problems]
        lines.append(f"supervisor {name}: {'FAIL' if problems else 'pass'}")
        ok = ok and not problems
    return ok, lines


def montecarlo(paths):
    results = [check(p) for p in paths]
    passed = sum(1 for _, problems in results if not problems)
    lines = [f"mc {Path(p).stem}: {fmt(g)}{'' if not pr else ': ' + '; '.join(pr)}" for p, (g, pr) in zip(paths, results)]
    for key, label in (("vin_fall", "vin falling trip"), ("vin_rise", "vin rising trip"), ("mem_fall", "vdd_mem falling trip"), ("mem_rise", "vdd_mem rising trip")):
        values = [g[key] for g, _ in results if key in g and not math.isnan(g[key])]
        if len(values) > 1:
            lines.append(f"mc {label}: mean {statistics.mean(values):.4f} V, sigma {1000 * statistics.stdev(values):.2f} mV, min {min(values):.4f} V, max {max(values):.4f} V over {len(values)} runs")
    lines.append(f"mc yield {passed} of {len(paths)} seeds ({passed / len(paths):.1%}), one-sided 95% lower bound {lower_bound(passed, len(paths)):.1%}")
    ok = passed / len(paths) >= YIELD
    lines.append(f"mc: {'pass' if ok else 'FAIL'} (limit {YIELD:.0%} of seeds)")
    return ok, lines


if __name__ == "__main__":
    mode, *files = sys.argv[1:]
    ok, lines = {"detector": detector, "supervisor": supervisor, "mc": montecarlo}[mode](files)
    print("\n".join(lines))
    sys.exit(0 if ok else 1)
