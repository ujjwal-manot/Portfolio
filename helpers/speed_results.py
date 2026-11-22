# Reads the standard cell speed sweeps (speed_<corner>.txt from tests/speed.cir) and the library's own delays (fo4_<corner>.txt from tests/fo4.tcl): checks that the transistor sweep gives the library's slow/typ and fast/typ ratios to within 5%, and prints how much slower the cells are at each supply (with bitcell, from two read_<corner>.txt tables of the SRAM bitcell's read current, how much longer the bit lines take at ss -40 C than at ss 125 C, current being what discharges them) than at the slow library's point (ss, 125 C, 1.08 V), worst over the slow-process corners and the three cells.
import sys
from pathlib import Path

LIMIT, POINTS = 0.05, {"slow": ("ss_125", 1.08), "fast": ("ff_m40", 1.32)}

def read_sweep(path):
    lines = Path(path).read_text().split("\n")
    names = lines[0].split()[1:]
    return {round(float(r[0]), 2): dict(zip(names, map(float, r[1:]))) for r in (l.split() for l in lines[1:] if l.strip())}

def read_library(path):
    words = Path(path).read_text().split()
    return words[0], {words[i]: float(words[i + 1]) for i in range(1, len(words), 2)}

def slowdown(sweeps):
    base = sweeps["ss_125"][1.08]
    return {v: max(sweeps[c][v][k] / base[k] for c in sweeps if c.startswith("ss") for k in base) for v in sweeps["ss_125"]}

def ratio_errors(sweeps, library):
    typ = sweeps["tt_25"][1.2]
    return {(k, cell): (sweeps[c][v][cell] / typ[cell]) / (library[k][cell] / library["typ"][cell]) - 1 for k, (c, v) in POINTS.items() for cell in typ}

def cold_read_slowdown(hot_path, cold_path):
    load = lambda p: {round(float(l.split()[0]), 2): float(l.split()[1]) for l in Path(p).read_text().split("\n")[1:] if l.strip()}
    hot, cold = load(hot_path), load(cold_path)
    return {v: hot[v] / cold[v] for v in hot if v in cold}

if __name__ == "__main__":
    if sys.argv[1] == "bitcell":
        for v, s in cold_read_slowdown(sys.argv[2], sys.argv[3]).items():
            print(f"vdd {v:.2f} V: bitcell read current at ss -40 C gives {s:.3f} x the bit line time at ss 125 C")
        sys.exit(0)
    sweeps, library = {}, {}
    for path in sys.argv[1:]:
        name = Path(path).stem
        if name.startswith("speed_"):
            sweeps[name[6:]] = read_sweep(path)
        else:
            k, delays = read_library(path)
            library[k] = delays
    typ = sweeps["tt_25"][1.2]
    for cell in typ:
        print(f"{cell}: transistors at tt 25 C 1.20 V {typ[cell] * 1e12:.1f} ps, library typ {library['typ'][cell] * 1e12:.1f} ps ({typ[cell] / library['typ'][cell] - 1:+.1%})")
    errors = ratio_errors(sweeps, library)
    for (k, cell), e in errors.items():
        print(f"{k}/typ ratio, {cell}: transistors differ from the library by {e:+.2%}")
    for v, s in slowdown(sweeps).items():
        print(f"vdd {v:.2f} V: worst slow-corner delay {s:.3f} x the slow library point")
    fails = [f"{k}/typ ratio of {cell} off by {e:+.2%}, limit {LIMIT:.0%}" for (k, cell), e in errors.items() if abs(e) > LIMIT]
    for f in fails:
        print("FAIL " + f)
    print("every check passes" if not fails else f"{len(fails)} failures")
    sys.exit(1 if fails else 0)
