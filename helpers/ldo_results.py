# Reads the LDO testbench results: in corners mode each corner file (one line per run: ldo_dc, psrr, step_0p5m, step_2m, loop_<load> and ldo_startup) must meet every limit (load regulation 5 mV from 0 to 2 mA, line regulation 10 mV/V, bandgap and LDO current 200 uA at 27 C and below, growing with absolute temperature above that because the bias is PTAT (265 uA at 125 C), the rail at or above 1.16 V through a 0.5 mA step, twice the opamp's worst supply current, and at or below 1.32 V after a 2 mA step and at start-up, phase margin 45 deg at every load, supply rejection 40 dB at 1 kHz and 20 dB at 1 MHz, start-up within 5% of 1.2063 V and settled in 200 us); in model mode the loop-gain measurement run on the ideal two-pole stand-in must match that loop's arithmetic: in mc mode (ss or ff, then mc.txt files from tests/ldo_mc.cir) it counts the runs meeting the limits that decide that corner and gives the yield's one-sided 95% lower bound; in study mode it prints current, dip and no-load margin of the design's corners beside a variant's (first half of the files, then the second): python3 ldo_results.py corners|model|study files...
import cmath, math, sys
from analog_results import lower_bound
from pathlib import Path

LIMITS = [("ldo_dc", "load_reg_v", "abs<=", 5e-3), ("ldo_dc", "line_v_per_v", "abs<=", 10e-3), ("step_0p5m", "dip_v", ">=", 1.16), ("step_2m", "peak_v", "<=", 1.32), ("psrr", "psrr_1k_db", ">=", 40), ("psrr", "psrr_1m_db", ">=", 20),
          ("ldo_startup", "top_v", "<=", 1.32), ("ldo_startup", "settle_s", "<=", 200e-6)]
GAIN, P1, P2 = 1000 * 10 / 10.1, 1e3, 1e6

def parse(path):
    runs = {}
    for line in Path(path).read_text().splitlines():
        f = line.split()
        if f:
            runs[f[0]] = {k: float(v) for k, v in zip(f[1::2], f[2::2])}
    return runs

def corner(path):
    runs, bad = parse(path), []
    words = Path(path).stem.split("_")
    temp = float(words[3].replace("m", "-")) if len(words) == 4 else 27.0
    iq_limit = 200e-6 * max(1.0, (temp + 273.15) / 300.15)
    iq = runs.get("ldo_dc", {}).get("iq_a", float("nan"))
    if not iq <= iq_limit:
        bad.append(f"ldo_dc iq_a {iq:.4g}, limit <= {iq_limit:.4g} at {temp:g} C")
    for run, key, op, limit in LIMITS:
        value = runs.get(run, {}).get(key, float("nan"))
        ok = abs(value) <= limit if op == "abs<=" else value <= limit if op == "<=" else value >= limit
        if not ok:
            bad.append(f"{run} {key} {value:.4g}, limit {op} {limit:g}")
    loops = {r: v for r, v in runs.items() if r.startswith("loop_")}
    bad += [f"{r} phase margin {v.get('pm_deg', float('nan')):.3g} deg, limit 45" for r, v in loops.items() if not v.get("pm_deg", 0) >= 45]
    if not loops:
        bad.append("no loop-gain run")
    start = runs.get("ldo_startup", {}).get("final_v", 0)
    if not abs(start / 1.2063 - 1) <= 0.05:
        bad.append(f"start-up ends at {start:.4g} V")
    return not bad, runs, bad

def t(f):
    return GAIN / ((1 + 1j * f / P1) * (1 + 1j * f / P2))

def expected():
    lo, hi = 1.0, 1e10
    for _ in range(200):
        mid = math.sqrt(lo * hi)
        lo, hi = (mid, hi) if abs(t(mid)) > 1 else (lo, mid)
    return {"gain_db": 20 * math.log10(GAIN), "fc_hz": lo, "pm_deg": 180 + math.degrees(cmath.phase(t(lo)))}

def model(path):
    got, want = parse(path)["loop"], expected()
    tolerance = {"gain_db": 0.05, "fc_hz": 0.01 * want["fc_hz"], "pm_deg": 0.5}
    rows = {k: (got.get(k, float("nan")), v, abs(got.get(k, float("nan")) - v) <= tolerance[k]) for k, v in want.items()}
    return all(r[2] for r in rows.values()), rows

def monte_carlo(paths, kind):
    hot_limit = 200e-6 * (125 + 273.15) / 300.15
    ok = lambda v: v["dip_v"] >= 1.16 and v["pm_deg"] >= 45 if kind == "ss" else v["iq_a"] <= hot_limit
    runs = [parse(p)["mc"] for p in paths]
    passed = sum(ok(v) for v in runs)
    return {"passed": passed, "runs": len(runs), "lower": lower_bound(passed, len(runs)), "values": runs}

def summary(path):
    runs = parse(path)
    return runs["ldo_dc"]["iq_a"], runs["step_0p5m"]["dip_v"], runs["loop_0"]["pm_deg"]

if __name__ == "__main__":
    mode, paths = sys.argv[1], sys.argv[2:]
    if mode == "mc":
        r = monte_carlo(paths[1:], paths[0])
        for key in ("dip_v", "pm_deg", "iq_a", "code"):
            xs = [v[key] for v in r["values"]]
            mean = sum(xs) / len(xs)
            sigma = (sum((x - mean) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5
            print(f"{key}: mean {mean:.5g} sigma {sigma:.3g} min {min(xs):.5g} max {max(xs):.5g}")
        print(f"{r['passed']} of {r['runs']} runs meet the limits ({'rail at or above 1.16 V through the 0.5 mA step and no-load phase margin 45 deg' if paths[0] == 'ss' else 'current at or below 265 uA at 125 C'}); yield is at least {r['lower']:.3f} at 95% confidence")
        ok = r["passed"] == r["runs"]
    elif mode == "study":
        half = len(paths) // 2
        for a, b in zip(paths[:half], paths[half:]):
            (ia, da, pa), (ib, db, pb) = summary(a), summary(b)
            print(f"{Path(a).stem}: design {ia * 1e6:.1f} uA, dip {da:.4f} V, no-load margin {pa:.1f} deg; variant {ib * 1e6:.1f} uA, dip {db:.4f} V, no-load margin {pb:.1f} deg")
        ok = True
    elif mode == "model":
        ok, rows = model(paths[0])
        for k, (g, w, p) in rows.items():
            print(f"{k:8} measured {g:.6g} expected {w:.6g} {'ok' if p else 'MISMATCH'}")
        print("loop-gain measurement matches the arithmetic" if ok else "loop-gain measurement does not match the arithmetic")
    else:
        ok = True
        for p in sorted(paths):
            good, runs, bad = corner(p)
            ok &= good
            print(Path(p).stem, " ".join(f"{r}.{k}={v:.4g}" for r, kv in runs.items() for k, v in kv.items()))
            for b in bad:
                print(f"FAIL {Path(p).stem}: {b}")
        print("every corner meets every limit" if ok else "some corner misses a limit")
    sys.exit(0 if ok else 1)
