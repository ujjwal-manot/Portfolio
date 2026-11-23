# Extra bandgap_ldo checks: pex mode reads a Magic extracted netlist and fails a diode line (a junction counted twice), a device model outside the thick-oxide MOS, rppd, rhigh and MIM set, a capacitor across a MIM's two plates or a resistor across a resistor device's two ends (both counted twice), and lists the resistor segments by size; clean mode prints an extracted netlist without the capacitors Magic puts across a MIM's plates (its TopMetal1 over Metal5 area cap, which the cap_cmim model already holds) and names each dropped line on stderr; startup mode holds ldo_startup lines to the LDO's start-up limits from ldo_results.py (within 5% of 1.2063 V, at most 1.32 V, settled in 200 us); load mode holds load lines (the rail's lowest and highest point under the ADC's switching load) to 1.16 V and 1.32 V; nan or missing values fail: python3 bandgap_ldo_checks.py pex|clean|startup|load files...
import math, sys
from collections import Counter
from pathlib import Path
from ldo_results import LIMITS, parse

MODELS = {"sg13_hv_nmos", "sg13_hv_pmos", "rppd", "rhigh", "cap_cmim"}
TOP = dict(((r, k), v) for r, k, _, v in LIMITS)

def pex(text):
    bad, segments, caps, resistors, plain = [], Counter(), {}, {}, []
    for line in text.splitlines():
        w = line.split()
        if not w or w[0][0] in "*.+":
            continue
        kind = w[0][0].upper()
        if kind == "D":
            bad.append(f"FAIL {w[0]}: a diode line, so a junction the MOS model already holds is counted twice")
        elif kind == "X":
            model = [x for x in w[1:] if "=" not in x][-1]
            nodes = [x for x in w[1:] if "=" not in x][:-1]
            if model not in MODELS:
                bad.append(f"FAIL {w[0]}: device model {model} is not one this block draws")
            if model == "cap_cmim":
                caps[frozenset(nodes[:2])] = w[0]
            if model in ("rppd", "rhigh"):
                resistors[frozenset(nodes[:2])] = w[0]
                size = dict(x.split("=") for x in w if "=" in x)
                segments[f"{model} w={size.get('w')} l={size.get('l')}"] += 1
        elif kind in "RC":
            plain.append((kind, w[0], frozenset(w[1:3])))
    for kind, name, pair in plain:
        if kind == "C" and pair in caps:
            bad.append(f"FAIL {name}: a capacitor across the plates of {caps[pair]}, counted twice")
        if kind == "R" and pair in resistors:
            bad.append(f"FAIL {name}: a resistor across the ends of {resistors[pair]}, counted twice")
    lines = [f"{k}: {n}" for k, n in sorted(segments.items())] + bad
    return not bad, lines

def clean(text):
    plain = [[x for x in l.split() if "=" not in x] for l in text.splitlines() if l[:1] and l[:1] in "Xx"]
    plates = {frozenset(w[1:3]) for w in plain if w[-1] == "cap_cmim"}
    out, dropped = [], []
    for line in text.splitlines():
        w = line.split()
        (dropped if w and w[0][:1] in "Cc" and frozenset(w[1:3]) in plates else out).append(line)
    return "\n".join(out) + "\n", dropped

def startup(paths):
    ok, lines = True, []
    for p in paths:
        r = parse(p).get("ldo_startup", {})
        final, top, settle = (r.get(k, math.nan) for k in ("final_v", "top_v", "settle_s"))
        good = abs(final / 1.2063 - 1) <= 0.05 and top <= TOP[("ldo_startup", "top_v")] and settle <= TOP[("ldo_startup", "settle_s")]
        ok &= good
        lines.append(f"{'ok  ' if good else 'FAIL'} {Path(p).stem}: final {final:.5g} V, highest {top:.5g} V, settled {settle * 1e6:.4g} us after the ramp")
    return ok, lines

def load(paths):
    ok, lines = True, []
    for p in paths:
        r = parse(p).get("load", {})
        low, high = r.get("min_v", math.nan), r.get("max_v", math.nan)
        good = low >= TOP[("step_0p5m", "dip_v")] and high <= TOP[("step_2m", "peak_v")]
        ok &= good
        lines.append(f"{'ok  ' if good else 'FAIL'} {Path(p).stem}: rail between {low:.5g} and {high:.5g} V, limits {TOP[('step_0p5m', 'dip_v')]:g} and {TOP[('step_2m', 'peak_v')]:g} V")
    return ok, lines

if __name__ == "__main__":
    mode, paths = sys.argv[1], sys.argv[2:]
    if mode == "clean":
        out, dropped = clean(Path(paths[0]).read_text())
        sys.stdout.write(out)
        sys.stderr.write("".join(f"dropped {l}\n" for l in dropped))
        sys.exit(0)
    if mode == "pex":
        ok, lines = True, []
        for p in paths:
            good, found = pex(Path(p).read_text())
            ok &= good
            lines += [p] + ["  " + l for l in found]
    else:
        ok, lines = (startup if mode == "startup" else load)(paths)
    print("\n".join(lines))
    print("every check passes" if ok else "some check fails")
    sys.exit(0 if ok else 1)
