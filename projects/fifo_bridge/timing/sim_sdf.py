# Writes the SDF copy Icarus can use: each cell's conditional IOPATH arcs (which Icarus ignores) become one unconditional arc per input and output holding the slowest of them, and each wire to or from a top-level port (which Icarus cannot place) is removed and its slower edge added to the arcs of the cell pin it touches, so every path keeps the delay STA gave it: python3 sim_sdf.py full.sdf sim.sdf.
import re, sys

ARC = re.compile(r"\(IOPATH (\S+) (\S+) ((?:\([^()]*\)\s*)+)\)")
WIRE = re.compile(r"\(INTERCONNECT (\S+) (\S+) ((?:\([^()]*\)\s*)+)\)")

def numbers(text):
    return [float(v) for v in re.findall(r"[\d.]+", text)]

def slowest(values, extra):
    found = [float(v) for v in values if v]
    return f"{max(found) + extra:.4f}" if found else ""

def merge(arcs, extra):
    edges = [re.findall(r"\(([^()]*)\)", a) for a in arcs]
    return " ".join("(" + ":".join(slowest(f, extra) for f in zip(*(e.split(":") for e in edge))) + ")" for edge in zip(*edges))

def convert(sdf):
    divider = re.escape(re.search(r"\(DIVIDER (\S)\)", sdf).group(1))
    split = lambda end: re.split(rf"(?<!\\){divider}", end)
    extra = {}
    for a, b, delays in WIRE.findall(sdf):
        if len(split(a)) == 1:
            extra[("in", *split(b))] = max(numbers(delays))
        elif len(split(b)) == 1:
            extra[("out", *split(a))] = max(numbers(delays))
    out = []
    for block in re.split(r"(?=\n \(CELL\n)", sdf):
        arcs = {}
        for pin, to, delays in ARC.findall(block):
            arcs.setdefault((pin, to), []).append(delays)
        if arcs:
            cell = re.search(r"\(INSTANCE (\S+)\)", block).group(1)
            start = block.index("(ABSOLUTE\n") + len("(ABSOLUTE\n")
            end = block.index("\n   )\n  )", start)
            body = [f"    (IOPATH {p} {t} {merge(a, extra.get(('in', cell, p), 0) + extra.get(('out', cell, t), 0))})" for (p, t), a in arcs.items()]
            block = block[:start] + "\n".join(body) + block[end:]
        else:
            block = "\n".join(line for line in block.split("\n") if not ((w := WIRE.search(line)) and min(len(split(e)) for e in w.groups()[:2]) == 1))
        out.append(block)
    return "".join(out)

if __name__ == "__main__":
    open(sys.argv[2], "w").write(convert(open(sys.argv[1]).read()))
