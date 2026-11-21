# Reads the ngspice transistor sweeps (tests/charts.cir in the opamp project, one file per corner and temperature, at source-to-bulk 0 and 0.25 V) and prints each device's threshold two ways (the model's own value, and the maximum-gm line extrapolated at 50 mV drain) for every corner, plus gm/Id tables at 0.6 V drain for the typical corner; opamp_sizing.py reads the same tables.
import sys
from pathlib import Path

NAMES = ("ids", "gm", "gds", "cgg", "vth", "vdss", "fug", "sid", "sfl")
W = 5e-6
TARGETS = (6, 8, 10, 12, 14, 16, 18, 20)

def read(path):
    out = {}
    for line in Path(path).read_text().splitlines():
        f = line.split()
        if f[0] == "l":
            l, vds, vsb = round(float(f[1].rstrip("u")) * 1e-6, 9), float(f[3]), float(f[5])
            continue
        v = list(map(float, f))
        for i, d in enumerate("np"):
            out.setdefault((d, l, vds, vsb), []).append({"vgs": v[0], **dict(zip(NAMES, v[1 + 9 * i:10 + 9 * i]))})
    return out

def threshold(rows, vds):
    best = max(rows, key=lambda r: r["gm"])
    return best["vgs"] - best["ids"] / best["gm"] - vds / 2

def table(rows):
    top = max(range(len(rows)), key=lambda i: rows[i]["gm"] / rows[i]["ids"])
    falling = rows[top:]
    out = []
    for g in TARGETS:
        pair = next(((a, b) for a, b in zip(falling, falling[1:]) if a["gm"] / a["ids"] >= g > b["gm"] / b["ids"]), None)
        if pair:
            a, b = pair
            t = (a["gm"] / a["ids"] - g) / (a["gm"] / a["ids"] - b["gm"] / b["ids"])
            out.append({"gm_id": g, **{k: a[k] + t * (b[k] - a[k]) for k in a}})
    return out

if __name__ == "__main__":
    data = {Path(p).stem.removeprefix("charts_"): read(p) for p in sys.argv[1:]}
    lengths = sorted({k[1] for k in next(iter(data.values()))})
    print("threshold at 50 mV drain, model / max-gm extrapolation (V); PMOS as magnitudes")
    print("corner   " + "".join(f"{d.upper()} L={l * 1e6:<5g}      " for d in "np" for l in lengths))
    for name, sweep in sorted(data.items()):
        print(f"{name:8} " + "".join(f"{sweep[(d, l, 0.05, 0.0)][0]['vth']:.3f}/{threshold(sweep[(d, l, 0.05, 0.0)], 0.05):.3f}     " for d in "np" for l in lengths))
    for d in "np":
        for l in lengths:
            print(f"\ntt_27 {d.upper()}MOS L = {l * 1e6:g} um, W = 5 um, |Vds| = 0.6 V")
            print("gm/Id   |Vgs|    Id/W(A/m)  gm/gds   fT(GHz)  |Vdsat|")
            for r in table(data["tt_27"][(d, l, 0.6, 0.0)]):
                print(f"{r['gm_id']:5.0f}  {r['vgs']:6.3f}  {r['ids'] / W:9.3f}  {r['gm'] / r['gds']:7.1f}  {r['fug'] / 1e9:7.2f}  {r['vdss']:6.3f}")
