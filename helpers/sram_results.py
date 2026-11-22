# Checks cpu tests/sram_hold.cir: every copy of the SRAM sense amplifier flip-flop must give the decision its split asks for (QP high, but low for case b0 whose split is reversed) within a tenth of the supply of the rail 10 ns after the read, and still hold it within a tenth of the supply after 1 ms, reported per corner as its file name gives it: python3 sram_results.py hold.txt ...
import sys
from pathlib import Path

def held(path):
    problems = []
    for line in open(path).readlines()[1:]:
        case, early, late, vdd = line.split()[0], *map(float, line.split()[1:])
        want = 0 if case == "b0" else vdd
        if abs(early - want) > 0.1 * vdd:
            problems.append(f"{path}: case {case} read {early:.4g} V, expected {want:.4g} V")
        elif abs(late - early) > 0.1 * vdd:
            problems.append(f"{path}: case {case} moved from {early:.4g} to {late:.4g} V in 1 ms")
    return problems

def label(path):
    process, temp, supply = Path(path).stem.split("_")[-3:]
    return f"{process} {temp.replace('m', '-')} C {supply.replace('v', '.')} V"

if __name__ == "__main__":
    fails = []
    for path in sys.argv[1:]:
        p = held(path)
        print(f"{label(path)}: {'every case holds for 1 ms' if not p else 'fails'}")
        fails += p
    for f in fails:
        print("FAIL " + f)
    print("every check passes" if not fails else f"{len(fails)} failures")
    sys.exit(1 if fails else 0)
