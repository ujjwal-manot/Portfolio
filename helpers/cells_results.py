# Checks power_manager's layout against its schematic from ngspice's own output files, each extracted file (name with _ext_) beside its schematic twin (_sch_): unit (extracted on-current within 2% of the schematic's, both switching delays under 10 ns, half the 20 ns controller clock), cmp (the bisection replayed from its echoed steps, extracted systematic offset within 1 mV, a sixth of the 6 mV ladder step, decision delay at 1 mV under 10 ns) and array (extracted all-on current at least 98% of the schematic's); any missing or unreadable value fails: python3 cells_results.py unit|cmp|array <ext files>
import math, re, sys
from pathlib import Path

def number(text):
    try:
        v = float(text)
    except ValueError:
        return None
    return v if math.isfinite(v) else None

def fields(path):
    words = Path(path).read_text().split()
    return {k: number(v) for k, v in zip(words[1::2], words[2::2])}

def twin(path):
    return Path(str(path).replace("_ext_", "_sch_"))

def corner(path):
    return re.sub(r"^\w+?_ext_", "", Path(path).stem)

def unit(path):
    ext, sch = fields(path), fields(twin(path))
    keys = ["i_on_a", "t_on_s", "t_off_s", "i_vin_on_a", "i_vin_off_a", "i_off_a"]
    if any(ext.get(k) is None or sch.get(k) is None for k in keys):
        return False, f"{corner(path)}: missing or unreadable value"
    ratio = ext["i_on_a"] / sch["i_on_a"] - 1
    ok = abs(ratio) <= 0.02 and ext["t_on_s"] < 10e-9 and ext["t_off_s"] < 10e-9 and sch["i_on_a"] > 0
    return ok, (f"{corner(path)}: i_on {sch['i_on_a'] * 1e6:.1f} -> {ext['i_on_a'] * 1e6:.1f} uA ({ratio * 100:+.2f}%), "
                f"t_on {sch['t_on_s'] * 1e9:.3f} -> {ext['t_on_s'] * 1e9:.3f} ns, t_off {sch['t_off_s'] * 1e9:.3f} -> {ext['t_off_s'] * 1e9:.3f} ns, "
                f"vin current off {sch['i_vin_off_a'] * 1e9:.3f} -> {ext['i_vin_off_a'] * 1e9:.3f} nA")

def comparator(path):
    vdd = float(corner(path).split("_")[-1].replace("v", "."))
    steps = {"-50e-3": [], "50e-3": []}
    delays = {}
    for words in (l.split() for l in Path(path).read_text().splitlines()[1:]):
        if words[0] == "step" and len(words) == 4 and words[1] in steps:
            steps[words[1]].append((number(words[2]), number(words[3])))
        elif words[0] == "delay" and len(words) == 3:
            delays[words[1]] = number(words[2])
    found = {}
    for first, rows in steps.items():
        if len(rows) != 15 or any(v is None for row in rows for v in row):
            return None, f"{len(rows)} readable steps after {first}, needs 15"
        lo, hi = -20e-3, 20e-3
        for mid, out in rows:
            if abs(mid - (lo + hi) / 2) > 0.01 * (hi - lo):
                return None, f"step {mid} does not follow the bisection after {first}"
            lo, hi = (lo, mid) if out > vdd / 2 else (mid, hi)
        found[first] = (lo + hi) / 2
    if sorted(delays) != ["-1e-3", "1e-3"] or any(v is None or v <= 0 for v in delays.values()):
        return None, "missing or unreadable decision delay"
    return {"offset": (found["-50e-3"] + found["50e-3"]) / 2, "hysteresis": found["-50e-3"] - found["50e-3"], "delay": max(delays.values())}, ""

def cmp(path):
    ext, why = comparator(path)
    sch, why_sch = comparator(twin(path))
    if ext is None or sch is None:
        return False, f"{corner(path)}: {why or why_sch}"
    ok = abs(ext["offset"]) <= 1e-3 and ext["delay"] < 10e-9
    return ok, (f"{corner(path)}: offset {sch['offset'] * 1e3:.3f} -> {ext['offset'] * 1e3:.3f} mV, hysteresis {sch['hysteresis'] * 1e3:.3f} -> {ext['hysteresis'] * 1e3:.3f} mV, "
                f"decision delay at 1 mV {sch['delay'] * 1e9:.3f} -> {ext['delay'] * 1e9:.3f} ns")

def array(path):
    ext, sch = fields(path), fields(twin(path))
    if any(d.get(k) is None for d in (ext, sch) for k in ("i_rail_a", "i_vin_a")) or sch["i_rail_a"] <= 0:
        return False, f"{corner(path)}: missing or unreadable value"
    ratio = ext["i_rail_a"] / sch["i_rail_a"]
    return ratio >= 0.98, f"{corner(path)}: all 128 on {sch['i_rail_a'] * 1e3:.2f} -> {ext['i_rail_a'] * 1e3:.2f} mA ({(ratio - 1) * 100:+.2f}%)"

if __name__ == "__main__":
    check = {"unit": unit, "cmp": cmp, "array": array}[sys.argv[1]]
    bad = 0
    for path in sys.argv[2:]:
        ok, line = check(path)
        print(("pass " if ok else "FAIL ") + "schematic -> extracted, " + line)
        bad += not ok
    print(f"{len(sys.argv) - 2 - bad} of {len(sys.argv) - 2} corners pass")
    sys.exit(1 if bad or len(sys.argv) < 3 else 0)
