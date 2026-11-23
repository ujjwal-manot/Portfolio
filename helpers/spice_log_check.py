# Fails an ngspice run from its log, whatever ngspice's exit code says: a stopped analysis (timestep too small, iteration limit, no convergence, simulation aborted), any "Error:" line, a meas that failed, or a log that does not end with ngspice's own done line (the run was killed or cut short, or the bench has no quit); a measure may fail only if the bench echoes "may be absent: <name> (<reason>)", and warnings ngspice recovers from (a failed gmin or source stepping step, a singular matrix that stepping clears) or the word "failed" in the bench's own Circuit title do not count.
import re, sys
from pathlib import Path

STOPPED = re.compile(r"timestep too small|iteration limit|no convergence|without convergence|simulation\(s\) aborted|^\s*error\b", re.I)
MEASURE = re.compile(r"^\s*(?:error: measure\s+(\w+)\b|meas\s+\w+\s+(\w+)\b.*failed!?\s*$)", re.I)
ABSENT = re.compile(r"^may be absent: (\w+) \(\S.*\)\s*$")
DONE = re.compile(r"^ngspice-\d+ done$")

def problems(text):
    lines = text.splitlines()
    absent = {m.group(1).lower() for m in map(ABSENT.match, lines) if m}
    found = []
    for line in lines:
        if line.startswith("Circuit:"):
            continue
        measure = MEASURE.match(line)
        if measure:
            if (measure.group(1) or measure.group(2)).lower() not in absent:
                found.append(line.strip())
        elif STOPPED.search(line):
            found.append(line.strip())
    ending = [line.strip() for line in lines if line.strip()]
    if not ending or not DONE.match(ending[-1]):
        found.append("log does not end with ngspice's done line: the run was killed or cut short, or the bench has no quit")
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
