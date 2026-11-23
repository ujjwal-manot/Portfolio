# Reads the bandgap testbench results: in corners mode every corner must hold a trimmed box tempco of 30 ppm/C or less from -40 to 125 C with its trim code inside the range (0 or 15 means the trim ran out) and its trimmed vref within 0.75 of its measured trim step of 1.2063 V (rounding alone leaves half a step); in mc mode the trimmed and untrimmed tempco yield (pass at 99% or more trimmed) with the one-sided 95% lower bound on the trimmed yield, the spread of vref before and after trim and the trim codes used; in startup mode every supply ramp must leave vref within 5% of the 1.2063 V target and settled within 50 us of the ramp's end: python3 bandgap_results.py corners|mc|startup files...
import math, sys
from analog_results import lower_bound
from pathlib import Path

TC, YIELD, TARGET, SETTLE, AIM = 30.0, 0.99, 1.2063, 50e-6, 0.75

def parse(path):
    f = Path(path).read_text().split()
    return {k: float(v) for k, v in zip(f[1::2], f[2::2])}

def corners(paths):
    rows = {Path(p).stem: parse(p) for p in paths}
    bad = [f"{c}: tempco {r['tc_ppm_per_c']:.3g} ppm/C over {TC:g}" for c, r in rows.items() if not r["tc_ppm_per_c"] <= TC]
    bad += [f"{c}: trim code {r['code']:g} at the end of its range" for c, r in rows.items() if r["code"] in (0, 15)]
    bad += [f"{c}: trimmed vref {r['vref_v']:.5g} V is {abs(r['vref_v'] - TARGET) / abs(r['step_v']):.2f} trim steps from {TARGET:g} V, limit {AIM:g}"
            for c, r in rows.items() if not abs(r["vref_v"] - TARGET) <= AIM * abs(r["step_v"])]
    return not bad, rows, bad

def spread(values):
    mean = sum(values) / len(values)
    return mean, math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))

def montecarlo(paths):
    runs = [parse(p) for p in paths]
    r = {"runs": len(runs), "trimmed_yield": sum(x["tc_ppm_per_c"] <= TC for x in runs) / len(runs),
         "untrimmed_yield": sum(x["untrimmed_tc_ppm_per_c"] <= TC for x in runs) / len(runs),
         "untrimmed_v": spread([x["untrimmed_v"] for x in runs]), "trimmed_v": spread([x["vref_v"] for x in runs]),
         "codes": sorted({int(x["code"]) for x in runs}), "worst_tc": max(x["tc_ppm_per_c"] for x in runs)}
    r["ok"] = r["trimmed_yield"] >= YIELD and 0 not in r["codes"] and 15 not in r["codes"]
    return r

def startups(paths):
    rows = {Path(p).stem: parse(p) for p in paths}
    bad = [f"{c}: vref ends at {r['final_v']:.4g} V" for c, r in rows.items() if not abs(r["final_v"] / TARGET - 1) <= 0.05]
    bad += [f"{c}: settles {r['settle_s']:.3g} s after the ramp" for c, r in rows.items() if not r["settle_s"] <= SETTLE]
    return not bad, rows, bad

if __name__ == "__main__":
    mode, paths = sys.argv[1], sys.argv[2:]
    if mode == "mc":
        r = montecarlo(paths)
        print(f"{r['runs']} runs: tempco yield {r['untrimmed_yield']:.1%} untrimmed, {r['trimmed_yield']:.1%} trimmed (worst {r['worst_tc']:.3g} ppm/C)")
        print(f"vref mean {r['untrimmed_v'][0]:.5g} V sigma {r['untrimmed_v'][1] * 1e3:.3g} mV untrimmed, mean {r['trimmed_v'][0]:.5g} V sigma {r['trimmed_v'][1] * 1e3:.3g} mV trimmed")
        print(f"trim codes used {r['codes']}")
        print(f"trimmed tempco yield is at least {lower_bound(round(r['trimmed_yield'] * r['runs']), r['runs']):.4f} at 95% confidence (one-sided, {r['runs']} seeds)")
        ok, bad = r["ok"], [] if r["ok"] else ["trimmed tempco yield below 99% or a trim code at the end of its range"]
    else:
        ok, rows, bad = (corners if mode == "corners" else startups)(paths)
        for name, row in sorted(rows.items()):
            print(name, " ".join(f"{k}={v:.5g}" for k, v in row.items()))
    for b in bad:
        print("FAIL", b)
    print("every check passes" if ok else "some check fails")
    sys.exit(0 if ok else 1)
