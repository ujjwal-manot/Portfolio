# Fails an ngspice run from its log, whatever ngspice's exit code says: a stopped analysis (timestep too small, singular matrix, no convergence, iteration limit, source stepping failed, simulation aborted), any "Error:" line, a meas that failed, or a log that does not end with ngspice's own done line (the run was killed or cut short); a failed dynamic or true gmin step on its own is not a failure, since ngspice goes on to the next method and the run can still converge.
import re, sys
from pathlib import Path

FAILED = re.compile(r"timestep too small|singular matrix|no convergence|without convergence|iteration limit|source stepping failed|simulation\(s\) aborted|\berror:|\bmeas\w*\b.*\bfailed", re.I)
DONE = re.compile(r"^ngspice-\d+ done$")

def problems(text):
    found = [line.strip() for line in text.splitlines() if FAILED.search(line)]
    lines = text.strip().splitlines()
    if not lines or not DONE.match(lines[-1].strip()):
        found.append("log does not end with ngspice's done line: the run was killed or cut short")
    return found

if __name__ == "__main__":
    bad = 0
    for path in sys.argv[1:]:
        found = problems(Path(path).read_text(errors="replace"))
        print(f"{path}: {'FAIL' if found else 'ok'}")
        for line in found[:10]:
            print(f"  {line[:200]}")
        bad += bool(found)
    sys.exit(1 if bad else 0)
