# Reads a flattened Yosys JSON netlist and reports every clock domain crossing that is not a clean two-flop synchronizer, every multi-bit crossing, and every unsynchronized or foreign reset, minus waived crossings, and flags waivers that match nothing.
import fnmatch, json, re, sys
from collections import defaultdict

ASYNC = {"ARST", "SET", "CLR", "ALOAD", "AD"}
PASS = {"$not", "$logic_not", "$_NOT_", "$buf", "$pos", "$_BUF_"}

def find(netlist, top, ports, waivers=()):
    m = json.load(open(netlist))["modules"][top]
    driver, loads, name = {}, defaultdict(list), {}
    for net, info in sorted(m["netnames"].items(), key=lambda kv: (kv[1].get("hide_name", 0), len(kv[0]))):
        for i, b in enumerate(info["bits"]):
            name.setdefault(b, net if len(info["bits"]) == 1 else f"{net}[{i}]")
    for port, p in m["ports"].items():
        if p["direction"] == "input":
            for b in p["bits"]:
                driver[b] = ("port", port)
    for cell, c in m["cells"].items():
        for pin, bits in c["connections"].items():
            for b in bits:
                if c["port_directions"].get(pin) == "output":
                    driver[b] = ("cell", cell)
                elif b not in ("0", "1", "x", "z"):
                    loads[b].append((cell, pin))
    cells = m["cells"]
    flop = {n for n, c in cells.items() if "CLK" in c["connections"]}
    clock = lambda f: name[cells[f]["connections"]["CLK"][0]]
    reg = lambda f: re.sub(r"\[\d+\]$", "", name[cells[f]["connections"]["Q"][0]])

    def domain(src):
        kind, what = src
        return clock(what) if kind == "cell" else ports.get(what, f"port {what}")

    def cone(bit, seen):
        if bit in ("0", "1", "x", "z") or bit in seen or bit not in driver:
            return set(), 0
        seen.add(bit)
        kind, what = driver[bit]
        if kind == "port" or what in flop:
            return {driver[bit]}, 0
        out, depth = set(), 0
        for pin, bits in cells[what]["connections"].items():
            if cells[what]["port_directions"].get(pin) == "input":
                for b in bits:
                    s, d = cone(b, seen)
                    out |= s
                    depth = max(depth, d)
        return out, depth + 1

    def through(bit):
        while bit in driver and driver[bit][0] == "cell" and cells[driver[bit][1]]["type"] in PASS:
            bit = cells[driver[bit][1]]["connections"]["A"][0]
        return driver.get(bit, ("const", bit))

    found, crossings = [], defaultdict(set)
    for f in sorted(flop):
        here, c = clock(f), cells[f]["connections"]
        for pin, bits in c.items():
            if pin in ASYNC | {"CLK"} or cells[f]["port_directions"].get(pin) != "input":
                continue
            for bit in bits:
                sources, depth = cone(bit, set())
                foreign = {s for s in sources if domain(s) != here}
                if not foreign:
                    continue
                q = c["Q"][bits.index(bit)] if pin == "D" else None
                if depth or pin != "D" or len(foreign) > 1:
                    found.append(("logic_before_sync", f"{reg(f)} on {here} samples {', '.join(sorted(s[1] if s[0] == 'port' else reg(s[1]) for s in foreign))} through logic"))
                    continue
                src = foreign.pop()
                users = loads[q]
                if len(users) != 1 or any(u not in flop or p != "D" or clock(u) != here for u, p in users):
                    found.append(("meta_fanout", f"first synchronizer flop {name[q]} on {here} feeds anything but one flop on its own clock"))
                crossings[(src[1] if src[0] == "port" else reg(src[1]), reg(f))].add(bit)
        for pin in ASYNC & c.keys():
            kind, what = through(c[pin][0])
            if kind == "cell" and what in flop and clock(what) != here:
                found.append(("reset_crossing", f"{reg(f)} on {here} is reset by {reg(what)} on {clock(what)}"))
            elif kind == "port":
                d = through(c["D"][0]) if "D" in c else None
                chained = d and (d[0] == "const" or (d[0] == "cell" and d[1] in flop and through(cells[d[1]]["connections"].get(pin, ["x"])[0]) == (kind, what)))
                if not chained:
                    found.append(("raw_reset", f"{reg(f)} on {here} is released straight from input {what}"))
    for (src, dst), bits in sorted(crossings.items()):
        if len(bits) > 1:
            found.append(("multibit", f"{src} -> {dst}: {len(bits)} bits cross separately"))
    used = {w for f in found for w in waivers if fnmatch.fnmatch(f[1], w)}
    found = [f for f in dict.fromkeys(found) if not any(fnmatch.fnmatch(f[1], w) for w in used)]
    return found + [("unused_waiver", w) for w in waivers if w not in used]

if __name__ == "__main__":
    netlist, top, waiver_file, *pairs = sys.argv[1:]
    waivers = [l.split(" : ")[0].strip() for l in open(waiver_file) if " : " in l]
    found = find(netlist, top, dict(p.split("=") for p in pairs), waivers)
    for rule, why in found:
        print(f"{rule:18} {why}")
    print(f"{len(found)} unwaived crossing problems, {len(waivers)} waivers")
    sys.exit(1 if found else 0)
