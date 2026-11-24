# Reads the opamp testbench results: in corners mode it lists every corner, names the worst corner for each chip.md spec and fails if any corner misses one or a measurement failed (including settling into the ADC's real capacitor DAC to half an LSB, 0.8 V / 256 / 2, and the opamp's error at the peak of the largest sensor signal chip.md allows (-1 dBFS, 0.357 V), twice its input offset (noise gain 2) plus its gain error times that peak, within the headroom left once the ADC's own allowed offset (1 LSB) and gain error (2 LSB over full scale, scaled to the peak) are taken out; swing is not required at the 1.08 V supply, below the 1.16 V the opamp needs for a 0.2 to 1.0 V output); in mc mode it counts yield per spec and combined (pass at 99% or more) with the one-sided 95% lower bound on the combined yield and the offset spread; in model mode it checks the two-pole model's measured loop gain, GBW and phase margin against the arithmetic for that model.
import cmath, math, sys
from pathlib import Path

LSB, PEAK = 0.8 / 256, 0.4 * 10 ** (-1 / 20)
OPAMP_SHARE_V = (0.4 - PEAK) - (1 + 2 * PEAK / 0.8) * LSB
SPECS = {"a0_db": (">=", 66), "gbw_hz": (">=", 20e6), "pm_deg": (">=", 60), "slew_v_per_s": (">=", 10e6), "settle_s": ("<=", 200e-9),
         "supply_a": ("<=", 500e-6), "settle_load_v": ("<=", 0.8 / 256 / 2),
         "edge_error_v": ("<=", OPAMP_SHARE_V), "out_low_v": ("<=", 0.2), "out_high_v": (">=", 1.0)}
REPORT = ("band_v_rms", "total_v_rms", "psrr_1k_db", "psrr_1m_db", "sampled_v_rms", "error_at_50ns_v", "kick_v")
SWING, NO_SWING_AT, YIELD = ("out_low_v", "out_high_v"), "_lo", 0.99
A0, BETA, P1, P2 = 1e4, 0.5, 1 / (2 * math.pi * 1e6 * 10e-12), 1 / (2 * math.pi * 1e4 * 159.2e-15)
TOLERANCE = {"a0_db": 0.1, "fc_hz": 0.02, "pm_deg": 1.0, "gbw_hz": 0.02, "ugf_hz": 0.02}

def parse(path):
    out = {}
    for line in Path(path).read_text().splitlines():
        f = line.split()
        out.update({k: float(v) for k, v in zip(f[1::2], f[2::2])})
    return out

def measured(r):
    keys = {"a0_db", "gbw_hz", "pm_deg", "supply_a", "out_low_v", "out_high_v", "offset_v", "settle_load_v"}
    m = {k: r[k] for k in keys if k in r}
    if {"rise_slew_v_per_s", "fall_slew_v_per_s"} <= r.keys():
        m["slew_v_per_s"] = min(r["rise_slew_v_per_s"], r["fall_slew_v_per_s"])
    if {"offset_v", "gain_error"} <= r.keys():
        m["edge_error_v"] = 2 * abs(r["offset_v"]) + abs(r["gain_error"]) * PEAK
    if {"rise_settle_s", "fall_settle_s"} <= r.keys() and min(r["rise_settle_s"], r["fall_settle_s"]) > 0:
        m["settle_s"] = max(r["rise_settle_s"], r["fall_settle_s"])
    return m | {k: r[k] for k in REPORT if k in r}

def corners(paths):
    data = {Path(p).stem.removeprefix("corner_"): measured(parse(p)) for p in paths}
    ok, rows = True, {}
    for spec, (op, limit) in SPECS.items():
        checked = {c: m for c, m in data.items() if not (spec in SWING and c.endswith(NO_SWING_AT))}
        missing = [c for c, m in checked.items() if spec not in m or math.isnan(m[spec])]
        values = [(m[spec], c) for c, m in checked.items() if c not in missing]
        worst = min(values) if op == ">=" else max(values)
        passed = not missing and (worst[0] >= limit if op == ">=" else worst[0] <= limit)
        rows[spec] = (*worst, limit, op, passed, missing)
        ok &= passed
    for key in REPORT:
        rows[key] = max((m[key], c) for c, m in data.items()) if "psrr" not in key else min((m[key], c) for c, m in data.items())
    return ok, rows

def meets(m, spec):
    op, limit = SPECS[spec]
    return spec in m and (m[spec] >= limit if op == ">=" else m[spec] <= limit)

def montecarlo(paths):
    runs = [measured(parse(p)) for p in paths]
    yields = {spec: sum(meets(m, spec) for m in runs) / len(runs) for spec in SPECS}
    yields["combined"] = sum(all(meets(m, spec) for spec in SPECS) for m in runs) / len(runs)
    offsets = [m["offset_v"] for m in runs if "offset_v" in m]
    return yields["combined"] >= YIELD, yields, offsets

def lower_bound(passed, runs, confidence=0.95):
    lo, hi = 0.0, 1.0
    for _ in range(100):
        p = (lo + hi) / 2
        chance = sum(math.comb(runs, k) * p ** k * (1 - p) ** (runs - k) for k in range(passed, runs + 1))
        lo, hi = (lo, p) if chance > 1 - confidence else (p, hi)
    return lo

def t(f):
    return A0 * BETA / ((1 + 1j * f / P1) * (1 + 1j * f / P2))

def crossing(level):
    lo, hi = 1.0, 1e10
    for _ in range(200):
        mid = math.sqrt(lo * hi)
        lo, hi = (mid, hi) if abs(t(mid)) > level else (lo, mid)
    return lo

def expected():
    fc = crossing(1)
    return {"a0_db": 20 * math.log10(A0), "fc_hz": fc, "pm_deg": 180 + math.degrees(cmath.phase(t(fc))),
            "gbw_hz": abs(t(1e6)) / BETA * 1e6, "ugf_hz": crossing(BETA)}

def model(path):
    got, want = parse(path), expected()
    rows = {k: (got.get(k, float("nan")), v, abs(got.get(k, float("nan")) - v) <= (TOLERANCE[k] if k in ("a0_db", "pm_deg") else TOLERANCE[k] * v)) for k, v in want.items()}
    return all(r[2] for r in rows.values()), rows

if __name__ == "__main__":
    mode, *paths = sys.argv[1:]
    if mode == "model":
        ok, rows = model(paths[0])
        for k, (g, w, p) in rows.items():
            print(f"{k:8} measured {g:.6g} expected {w:.6g} {'ok' if p else 'MISMATCH'}")
        print("two-pole model matches the arithmetic" if ok else "two-pole model does not match the arithmetic")
    elif mode == "mc":
        ok, yields, offsets = montecarlo(paths)
        for spec, y in yields.items():
            print(f"{spec:14} yield {y:.1%} of {len(paths)} runs")
        if offsets:
            mean = sum(offsets) / len(offsets)
            sigma = math.sqrt(sum((o - mean) ** 2 for o in offsets) / (len(offsets) - 1))
            print(f"offset_v       mean {mean:.4g} sigma {sigma:.4g} worst {max(offsets, key=abs):.4g}")
        print(f"combined yield is at least {lower_bound(round(yields['combined'] * len(paths)), len(paths)):.1%} at 95% confidence")
        print(f"combined yield meets {YIELD:.0%}" if ok else f"combined yield below {YIELD:.0%}")
    else:
        for p in sorted(paths):
            m = measured(parse(p))
            print(Path(p).stem.removeprefix("corner_"), " ".join(f"{k}={v:.4g}" for k, v in sorted(m.items())))
        ok, rows = corners(paths)
        for spec, (value, corner, limit, op, passed, missing) in ((k, v) for k, v in rows.items() if k in SPECS):
            print(f"{spec:14} worst {value:.4g} at {corner}, spec {op} {limit:g}: {'pass' if passed else 'FAIL'}{' (measurement failed at ' + ', '.join(missing) + ')' if missing else ''}")
        for key in REPORT:
            print(f"{key:14} worst {rows[key][0]:.4g} at {rows[key][1]}")
        for p in sorted(paths):
            m, name = measured(parse(p)), Path(p).stem.removeprefix("corner_")
            if name.endswith(NO_SWING_AT):
                print(f"swing at 1.08 V, not required: {name} out_low_v={m.get('out_low_v', float('nan')):.4g} out_high_v={m.get('out_high_v', float('nan')):.4g}")
        for spec, row in rows.items():
            if spec in SPECS and not row[4]:
                print(f"FAIL {spec}")
        print("every corner meets every spec" if ok else "some corner misses a spec")
    sys.exit(0 if ok else 1)
