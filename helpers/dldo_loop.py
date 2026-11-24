# Reads digital LDO loop results: per scheduled segment of a loop run (time and rail from wrdata) the mean, ripple, lowest and highest rail and settling time against chip.md's limits (loop), a real-number model run against a transistor run within the allowed errors (compare), ripple and droop across controller gains (gains), the cpu's per-cycle current from OpenSTA window reports (cpu_load), the controller-alone co-simulation with both coarse comparators high (coarse), comparator Monte Carlo offsets against the fine window (offsets), the comparators' input residue at their sampling edge with the real ladder, muxes and divider (sense), the bandgap-fed ladder reference (ref) and the measured switch unit as a model include (unit): python3 dldo_loop.py loop|compare|gains|cpu_load|coarse|offsets|sense|ref|unit ...
import math, re, statistics, sys
from pathlib import Path

LADDER, DIVIDER = 201, 0.6
REGULATION, RIPPLE, ENVELOPE, BAND = 0.02, 0.03, 0.05, 0.035
UP_TIME, DOWN_TIME, OXIDE = 500e-9, 1e-6, 1.32
WINDOW = 400e-9
ALLOWED = {"mean_v": 3e-3, "ripple_v": 5e-3, "lo_v": 10e-3, "hi_v": 10e-3, "settle_s": 40e-9}
NAMES = {"mean_v": "mean", "ripple_v": "ripple", "lo_v": "lowest rail", "hi_v": "highest rail", "settle_s": "transition time"}

def setpoint(tap, vref):
    return vref * tap / LADDER / DIVIDER

def read_schedule(path):
    lines = [l.split() for l in Path(path).read_text().splitlines() if l.strip()]
    t_end = float(lines[0][1])
    return t_end, [{"name": n, "start": float(a), "end": float(b), "tap": int(k), "load": load, "kind": kind} for n, a, b, k, load, kind in lines[1:]]

def read_ref(path):
    return float(re.search(r"vref_v=(\S+)", Path(path).read_text()).group(1))

def read_trace(path):
    return [(float(r[0]), float(r[1])) for r in (l.split() for l in Path(path).read_text().splitlines()) if r]

def mean(points, a, b):
    inside = [i for i, (t, _) in enumerate(points) if a <= t < b]
    total = sum(points[i][1] * (min(points[i + 1][0] if i + 1 < len(points) else b, b) - points[i][0]) for i in inside)
    return total / (b - points[inside[0]][0])

def metrics(segments, vref, points):
    out = []
    for s in segments:
        sp = setpoint(s["tap"], vref)
        seg = [(t, v) for t, v in points if s["start"] <= t < s["end"]]
        tail = [v for t, v in seg if t >= s["end"] - WINDOW]
        out_of_band = [i for i, (t, v) in enumerate(seg) if abs(v - sp) > BAND * sp]
        if not out_of_band:
            settle = 0.0
        elif out_of_band[-1] == len(seg) - 1:
            settle = None
        else:
            settle = seg[out_of_band[-1] + 1][0] - s["start"]
        out.append(dict(s, setpoint_v=sp, mean_v=mean(points, s["end"] - WINDOW, s["end"]), ripple_v=max(tail) - min(tail),
                        lo_v=min(v for _, v in seg), hi_v=max(v for _, v in seg), settle_s=settle))
    return out

def truncated(points, t_end):
    if not points or points[-1][0] < t_end * (1 - 1e-6):
        return [f"run ended at {points[-1][0] if points else 0:.4g} s before its {t_end:.4g} s end"]
    if any(math.isnan(v) for _, v in points):
        return ["not a number in the rail"]
    return []

def describe(m):
    settle = "never" if m["settle_s"] is None else f"{m['settle_s'] * 1e9:.0f} ns"
    return (f"{m['name']} {m['kind']} at {m['setpoint_v']:.4f} V ({m['load']} load): mean {m['mean_v']:.4f} V, ripple {m['ripple_v'] * 1e3:.1f} mV, "
            f"lowest {m['lo_v']:.4f} V, highest {m['hi_v']:.4f} V, settles inside +-{BAND:.1%} in {settle}")

def limits(m):
    n, sp, fails = m["name"], m["setpoint_v"], []
    if m["load"] == "active":
        if abs(m["mean_v"] - sp) > REGULATION * sp:
            fails.append(f"{n} mean off the setpoint by more than 2%: {m['mean_v']:.4f} V against {sp:.4f} V")
        if m["ripple_v"] > RIPPLE * sp:
            fails.append(f"{n} ripple above 3% of the setpoint: {m['ripple_v'] * 1e3:.1f} mV")
    if m["kind"] in ("load_up", "load_down") and max(sp - m["lo_v"], m["hi_v"] - sp) > ENVELOPE * sp:
        fails.append(f"{n} rail outside the setpoint +-5%: {m['lo_v']:.4f} to {m['hi_v']:.4f} V")
    if m["kind"] in ("dvfs_up", "dvfs_down"):
        most = UP_TIME if m["kind"] == "dvfs_up" else DOWN_TIME
        if m["settle_s"] is None:
            fails.append(f"{n} never settles inside +-{BAND:.1%} of {sp:.4f} V")
        elif m["settle_s"] > most:
            fails.append(f"{n} transition slower than {most * 1e9:.0f} ns: {m['settle_s'] * 1e9:.0f} ns")
    if m["kind"] == "dvfs_up" and m["hi_v"] > min((1 + ENVELOPE) * sp, OXIDE):
        fails.append(f"{n} overshoot above the setpoint +5% or 1.32 V: {m['hi_v']:.4f} V")
    if m["kind"] == "dvfs_down" and m["lo_v"] < (1 - ENVELOPE) * sp:
        fails.append(f"{n} undershoot below the setpoint -5%: {m['lo_v']:.4f} V")
    return fails

def loop_report(schedule, ref, trace):
    t_end, segments = read_schedule(schedule)
    points = read_trace(trace)
    fails = truncated(points, t_end)
    if fails:
        return [], fails
    ms = metrics(segments, read_ref(ref), points)
    return [describe(m) for m in ms], [f for m in ms for f in limits(m)]

def compare(schedule, ref, model, transistor):
    t_end, segments = read_schedule(schedule)
    runs = [read_trace(model), read_trace(transistor)]
    fails = [f"{p}: {f}" for p, r in zip((model, transistor), runs) for f in truncated(r, t_end)]
    if fails:
        return [], fails
    a, b = (metrics(segments, read_ref(ref), r) for r in runs)
    lines = []
    for x, y in zip(a, b):
        keys = [k for k in ALLOWED if k != "settle_s" or x["kind"].startswith("dvfs")]
        errs = {k: (math.inf if (x[k] is None) != (y[k] is None) else 0.0 if x[k] is None else x[k] - y[k]) for k in keys}
        lines.append(f"{x['name']} {x['kind']}: model minus transistor " + ", ".join(f"{NAMES[k]} {e * (1e9 if k == 'settle_s' else 1e3):+.1f} {'ns' if k == 'settle_s' else 'mV'}" for k, e in errs.items()))
        fails += [f"{x['name']} {NAMES[k]} differs by {abs(e) * (1e9 if k == 'settle_s' else 1e3):.1f} {'ns' if k == 'settle_s' else 'mV'}, allowed {ALLOWED[k] * (1e9 if k == 'settle_s' else 1e3):.0f}" for k, e in errs.items() if abs(e) > ALLOWED[k]]
    return lines, fails

def gains(schedule, ref, runs):
    t_end, segments = read_schedule(schedule)
    lines, fails = [], []
    for label, path in runs:
        points = read_trace(path)
        bad = truncated(points, t_end)
        if bad:
            fails += [f"{label}: {f}" for f in bad]
            continue
        ms = metrics(segments, read_ref(ref), points)
        worst = max(ms[1:], key=lambda m: m["ripple_v"] / m["setpoint_v"])
        lines.append(f"gains {label}: ripple " + ", ".join(f"{m['name']} {m['ripple_v'] * 1e3:.1f}" for m in ms) + f" mV; worst {worst['ripple_v'] / worst['setpoint_v']:.2%} of the setpoint in {worst['name']}; lowest rail against its setpoint {min(m['lo_v'] - m['setpoint_v'] for m in ms[1:]) * 1e3:+.1f} mV; {len([f for m in ms for f in limits(m)])} limit failures")
    return lines, fails

def cpu_windows(path):
    text = Path(path).read_text()
    if "Warning 1452" in text:
        raise ValueError("a window's clock period differs from the SDC period, so its edges were miscounted")
    windows = []
    for block in re.split(r"^window ", text, flags=re.M)[1:]:
        cycle = int(block.split()[0])
        groups = {g: float(m.group(1)) for g in ("Sequential", "Combinational", "Macro") for m in [re.search(rf"^{g}\s+\S+\s+\S+\s+\S+\s+(\S+)", block, re.M)] if m}
        if len(groups) < 3 or any(math.isnan(v) for v in groups.values()):
            raise ValueError(f"window {cycle} has no complete power report")
        windows.append({"cycle": cycle, "cells_a": (groups["Sequential"] + groups["Combinational"]) / 1.2, "macro_a": groups["Macro"] / 1.2})
    return windows

def coarse(path, n, t_end, first=10e-9, period=20e-9):
    rows = [[float(v) for v in l.split()] for l in open(path) if l.strip()]
    if rows[-1][0] < t_end * (1 - 1e-6):
        return [], [f"run ended at {rows[-1][0]:.4g} s before its {t_end:.4g} s end"]
    at = lambda t: [r for r in rows if r[0] <= t + 1e-15][-1][1::2]
    word = lambda bits: sum(1 << i for i, b in enumerate(bits) if b > 0.6)
    lines, fails, edge = [], [], first
    while edge + 5e-9 <= rows[-1][0] + 1e-15:
        before, after = at(edge - 1e-9), at(edge + 5e-9)
        lo, hi, far_lo, far_hi, rst_n = (v > 0.6 for v in before[:5])
        if far_lo and far_hi and rst_n and not lo and not hi:
            count, new, drive = word(before[5:13]), word(after[5:13]), word(after[13:21])
            lines.append(f"both coarse high at edge {edge:.4g} s: count {count} {'held' if new == count else f'moved to {new}'}, drive {drive}")
            if new != count or drive != count:
                fails.append(f"both coarse high moved the count from {count} to {new} (drive {drive}) at edge {edge:.4g} s")
        edge += period
    if not lines:
        fails.append("both coarse high never applied with the fine comparators quiet")
    return lines, fails

def yield_lower_bound(passed, runs, confidence=0.95):
    if passed == 0:
        return 0.0
    tail = lambda p: sum(math.comb(runs, k) * p ** k * (1 - p) ** (runs - k) for k in range(passed, runs + 1))
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if tail(mid) < 1 - confidence else (lo, mid)
    return lo

def offsets(paths, limit):
    values, fails = [], []
    for p in paths:
        words = Path(p).read_text().split()
        v = float(dict(zip(words[::2], words[1::2])).get("offset_v", "nan"))
        if math.isnan(v):
            fails.append(f"not a number or missing offset in {p}")
        values.append(v)
    if fails:
        return [], fails
    sigma, passed = statistics.stdev(values), sum(abs(v) < limit for v in values)
    lines = [f"comparator offset over {len(values)} Monte Carlo runs (seeds 1 to {len(values)}, tt 27 C, 1.2 V): mean {statistics.mean(values) * 1e3:.3f} mV, sigma {sigma * 1e3:.3f} mV, 3 sigma {3 * sigma * 1e3:.3f} mV, worst {max(values, key=abs) * 1e3:.3f} mV",
             f"runs inside +-{limit * 1e3:.1f} mV (half the fine window): {passed} of {len(values)}, one-sided 95% lower bound on that yield {yield_lower_bound(passed, len(values)):.4f}"]
    if 3 * sigma > limit:
        fails.append(f"3 sigma offset above {limit * 1e3:.1f} mV: {3 * sigma * 1e3:.3f} mV")
    return lines, fails

def ref_inc(path):
    words = Path(path).read_text().split()
    v = dict(zip(words[::2], words[1::2]))
    vref = float(v.get("vref_v", "nan"))
    if math.isnan(vref) or not 1.1 < vref < 1.3:
        raise ValueError(f"{path}: analog rail {vref} V is not a running bandgap and LDO")
    return f".param vref_v={vref:.6g}\n"

def unit_inc(iv_path, delay_path, t_end):
    rows = [tuple(float(x) for x in l.split()[:2]) for l in Path(iv_path).read_text().splitlines() if l.strip()]
    words = Path(delay_path).read_text().split()[1:]
    d = {words[i]: float(words[i + 1]) for i in range(0, len(words) - 1, 2)}
    if any(math.isnan(i) or i <= 0 for _, i in rows) or any(math.isnan(d.get(k, math.nan)) or d[k] <= 0 for k in ("t_on_s", "t_off_s")) or d.get("t_end_s", 0) < t_end * (1 - 1e-6):
        raise ValueError(f"{iv_path} or {delay_path}: a failed, missing or truncated measurement")
    table = ", ".join(f"{v:.6g}, {i:.6g}" for v, i in rows)
    return f".func iunit(x) {{pwl(x, {table})}}\n.param t_on={d['t_on_s']:.6g} t_off={d['t_off_s']:.6g}\n"

def sense(paths, limit):
    lines, fails = [], []
    for p in map(Path, paths):
        rows = [l.split() for l in p.read_text().splitlines() if l.startswith("sense ")]
        if len(rows) != 4:
            fails.append(f"{p}: {len(rows)} setpoints instead of 4")
        for w in rows:
            v = {k: float(x) for k, x in zip(w[2::2], w[3::2])}
            if any(math.isnan(x) for x in v.values()) or len(v) < 15:
                fails.append(f"not a number or a missing measure in {p} at tap {w[1]}")
                continue
            res = {f"{c}_{e}": (v[f"{c}_{e}"] - v[f"ideal_{c}"]) - (v[f"fb_{e}"] - v["ideal_fb"]) for c in ("fl", "fh", "cl", "ch") for e in "ab"}
            worst = max(res, key=lambda k: abs(res[k]))
            lines.append(f"{p.parent.name} tap {w[1]}: worst differential residue {res[worst] * 1e3:+.2f} mV ({worst}), common mode on fb {(v['fb_a'] - v['ideal_fb']) * 1e3:+.1f} and {(v['fb_b'] - v['ideal_fb']) * 1e3:+.1f} mV")
            if abs(res[worst]) > limit:
                fails.append(f"sensing residue above {limit * 1e3:.1f} mV: {res[worst] * 1e3:+.2f} mV at {p.parent.name} tap {w[1]} ({worst})")
    return lines, fails

def finish(lines, fails):
    for l in lines:
        print(l)
    for f in fails:
        print("FAIL " + f)
    print("every check passes" if not fails else f"{len(fails)} failures")
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    mode, args = sys.argv[1], sys.argv[2:]
    if mode == "loop":
        finish(*loop_report(*args))
    elif mode == "compare":
        finish(*compare(*args))
    elif mode == "gains":
        finish(*gains(args[0], args[1], list(zip(args[2::2], args[3::2]))))
    elif mode == "cpu_load":
        w = cpu_windows(args[0])
        Path(args[1]).write_text("".join(f"{x['cycle']} {x['cells_a']:.6g} {x['macro_a']:.6g}\n" for x in w))
        idle = [x for x in w if x["cycle"] in (1, 2)]
        active = [x for x in w if x["cycle"] >= 4]
        steps = [b["cells_a"] - a["cells_a"] for a, b in zip(w, w[1:])]
        for x in w:
            print(f"cycle {x['cycle']}: cpu cells {x['cells_a'] * 1e3:.3f} mA, macros {x['macro_a'] * 1e3:.3f} mA")
        print(f"idle (reset cycles 1 and 2, clock running, logic held): cpu cells {statistics.mean(x['cells_a'] for x in idle) * 1e3:.3f} mA, macros {statistics.mean(x['macro_a'] for x in idle) * 1e3:.3f} mA")
        print(f"active (cycles 4 to {w[-1]['cycle']}): cpu cells mean {statistics.mean(x['cells_a'] for x in active) * 1e3:.3f} mA, lowest {min(x['cells_a'] for x in active) * 1e3:.3f} mA, highest {max(x['cells_a'] for x in active) * 1e3:.3f} mA; macros mean {statistics.mean(x['macro_a'] for x in active) * 1e3:.3f} mA")
        print(f"largest one-cycle rise of the cpu cells' current {max(steps) * 1e3:.3f} mA, largest fall {-min(steps) * 1e3:.3f} mA")
        finish([], [] if len(w) > 8 and [x["cycle"] for x in w] == list(range(len(w))) else ["windows missing"])
    elif mode == "coarse":
        finish(*coarse(args[0], int(args[1]), float(args[2])))
    elif mode == "sense":
        finish(*sense(args[1:], float(args[0])))
    elif mode == "offsets":
        finish(*offsets(args[1:], float(args[0])))
    elif mode == "ref":
        lines, fails = [], []
        for p in map(Path, args):
            try:
                text = ref_inc(p)
            except ValueError as e:
                fails.append(str(e))
                continue
            (p.parent / "ref.inc").write_text(text)
            vref = read_ref(p.parent / "ref.inc")
            lines.append(f"{p.parent.name}: analog rail {vref:.5f} V with the ladder on it, setpoints " + ", ".join(f"{setpoint(k, vref):.4f}" for k in (90, 100, 110, 120)) + f" V, {(vref - 1.206) * 1e3:+.2f} mV from the ideal 1.206 V source")
        finish(lines, fails)
    elif mode == "unit":
        Path(args[2]).write_text(unit_inc(args[0], args[1], float(args[3])))
        finish([f"{args[2]} written from {args[0]} and {args[1]}"], [])
