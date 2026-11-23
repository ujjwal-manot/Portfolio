# Electromigration check for the thick-oxide layouts drawn by hv_layout.py and row_layout.py, where every MOS source and drain climbs to its net's Metal4 track through one stack of single 0.19 um vias with a 0.2 um Metal3 or Metal5 strap, and every track is 0.2 um of Metal4: in probes mode it prints an ngspice .save line for the current of every MOS (ids), rppd and rhigh resistor (ibody) and pnpMPA terminal (ic, ib, ie) in the named blocks (path from the instance names, e.g. x2.xn); in check mode it reads those currents (ngspice "print all") and fails any device whose terminal current is over its stack's limit (0.3 mA through one contact on a single-finger device, else 0.4 mA through one via) any resistor over its body limit (rppd 1.2 mA and rhigh 0.6 mA per um of width) or its one contact, any pnp terminal over one contact, and any net whose track can carry more than 0.6 mA (Metal4 0.2 to 0.3 um wide), a net's track current bounded by half the sum of its terminal currents, or the whole sum on a port net, where the outside current also enters; a missing or nan current fails; limits from IHP's SG13G2 process specification Rev. 1.2, section 2.15 (libs.doc/doc/SG13G2_os_process_spec.pdf), rated at 105 C; a device given as path=vias,plate (e.g. x2.xn=30,3.0) has its own pins instead, via arrays of that many vias per level up to a Metal5 plate that wide (2 mA/um), so its current leaves the tracks: python3 em_check.py probes|check sizes.inc design.cir... -- x1=bandgap x2=ldo [x2.xn=30,3.0] [raw.txt].
import math, re, sys
from spice_flatten import subcircuits, work_out, value

MOS = ("sg13_hv_nmos", "sg13_hv_pmos", "sg13_lv_nmos", "sg13_lv_pmos")
CONTACT, VIA, TRACK, PLATE = 0.3e-3, 0.4e-3, 0.6e-3, 2e-3
BODY = {"rppd": 1.2e-3, "rhigh": 0.6e-3}

def devices(text, params, tops):
    subs, found = subcircuits(text), []
    def walk(name, nets, scope, path):
        sub = subs[name]
        local = dict(scope)
        local.update({k: work_out(v, scope) for k, v in sub["defaults"].items()})
        local.update(nets["params"])
        net = lambda n: nets["map"].get(n, n if n == "0" else path + "." + n)
        for words in sub["lines"]:
            given = dict(w.split("=", 1) for w in words[1:] if "=" in w)
            plain = [w for w in words[1:] if "=" not in w]
            child, nodes, inst = plain[-1], [net(n) for n in plain[:-1]], path + "." + words[0].lower()
            p = {k: work_out(v, local) for k, v in given.items() if k != "mm_ok"}
            if child in MOS:
                found.append({"path": inst, "model": child, "kind": "m", "d": nodes[0], "s": nodes[2], "fingers": int(p.get("ng", 1) * p.get("m", 1))})
            elif child in BODY:
                found.append({"path": inst, "model": child, "kind": "r", "a": nodes[0], "b": nodes[1], "w": p["w"]})
            elif child == "pnpMPA":
                found.append({"path": inst, "model": child, "kind": "q", "c": nodes[0], "b": nodes[1], "e": nodes[2]})
            elif child in subs:
                walk(child, {"map": dict(zip(subs[child]["ports"], nodes)), "params": p}, local, inst)
    for prefix, top in tops.items():
        walk(top, {"map": {q: prefix + ":" + q for q in subs[top]["ports"]}, "params": {}}, params, prefix)
    return found

def names(d):
    if d["kind"] == "m":
        return [(f"@n.{d['path']}.n{d['model']}[ids]", ("d", "s"))]
    if d["kind"] == "r":
        return [(f"@n.{d['path']}.nr1[ibody]", ("a", "b"))]
    return [(f"@q.{d['path']}.qpnpmpa[i{t}]", (t,)) for t in ("c", "b", "e")]

def probes(text, params, tops):
    return [f".save {n}" for d in devices(text, params, tops) for n, _ in names(d)]

def check(raw, text, params, tops, own={}):
    got = {m.group(1).lower(): float(m.group(2)) for m in re.finditer(r"^(@\S+\])\s*=\s*(\S+)", raw, re.M)}
    ok, lines, nets = True, [], {}
    for d in devices(text, params, tops):
        flows = [(abs(got.get(n.lower(), math.nan)), sides) for n, sides in names(d)]
        i = max(f for f, _ in flows) if all(f == f for f, _ in flows) else math.nan
        if d["path"] in own:
            vias, plate = own[d["path"]]
            limit, why = min(VIA * vias, PLATE * plate), f"own pins: {vias} vias per level, {plate:g} um Metal5 plate"
        elif d["kind"] == "r":
            limit, why = min(BODY[d["model"]] * d["w"] * 1e6, CONTACT), f"{d['model']} {d['w'] * 1e6:g} um wide, one contact"
        elif d["kind"] == "q":
            limit, why = CONTACT, "one contact per terminal"
        else:
            limit, why = (CONTACT, "one contact") if d["fingers"] == 1 else (VIA, "one via per level")
        good = i <= limit
        ok &= good
        lines.append(f"{'ok  ' if good else 'FAIL'} {d['path']} {i * 1e3:.4g} mA, limit {limit * 1e3:g} mA ({why})")
        if d["path"] in own:
            continue
        for f, sides in flows:
            for side in sides:
                nets.setdefault(d[side], []).append(f)
    for n, terms in sorted(nets.items()):
        block, port = n.split(":")[0].split(".")[0], ":" in n
        bound = sum(terms) if port else sum(terms) / 2
        good = bound <= TRACK
        ok &= good
        lines.append(f"{'ok  ' if good else 'FAIL'} {block} net {n.split(':')[-1] if port else n} track at most {bound * 1e3:.4g} mA, limit {TRACK * 1e3:g} mA (Metal4 0.2 um)")
    return ok, lines

if __name__ == "__main__":
    mode, sizes, *rest = sys.argv[1:]
    cut = rest.index("--")
    files, tail = rest[:cut], rest[cut + 1:]
    params = {"mm": 0}
    for k, v in re.findall(r"(\w+)=(\S+)", " ".join(l for l in open(sizes).read().splitlines() if l.startswith(".param"))):
        params[k] = value(v)
    text = "\n".join(open(f).read() for f in files)
    tops = dict(t.split("=") for t in tail if "=" in t and not t.endswith(".txt") and "," not in t)
    own = {k: (int(v.split(",")[0]), float(v.split(",")[1])) for k, v in (t.split("=") for t in tail if "," in t)}
    if mode == "probes":
        print("\n".join(probes(text, params, tops)))
        sys.exit(0)
    raw = open(next(t for t in tail if t.endswith(".txt"))).read()
    ok, lines = check(raw, text, params, tops, own)
    print("\n".join(lines))
    print("every device and track is inside its electromigration limit" if ok else "some device or track is over its electromigration limit")
    sys.exit(0 if ok else 1)
