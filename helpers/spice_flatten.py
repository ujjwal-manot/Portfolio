# Flattens a hierarchical SPICE netlist into device lines (MOS, resistors, MIM capacitors, pnp bipolars), so a layout's LVS reference and the simulated design come from the same file: ports map to the caller's nets, internal nets and device names take the instance path joined by "_", and {expressions} are worked out from the global .param values, then the subcircuit's defaults, then the instance's own values, an m on a subcircuit instance multiplying every device inside it; mm_ok is dropped, any line it cannot carry into the reference (a non-X element or a .param inside a subcircuit, a continuation line, a ^ in an expression) stops it, and `python3 spice_flatten.py top sizes.inc design.cir ...` prints CDL with the device lines IHP's LVS reader takes.
import re, sys

SCALE = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3, "meg": 1e6}
MODELS = {"sg13_lv_nmos": "M", "sg13_lv_pmos": "M", "sg13_hv_nmos": "M", "sg13_hv_pmos": "M", "rhigh": "R", "rppd": "R", "rsil": "R", "cap_cmim": "C", "pnpMPA": "Q"}

def value(text):
    m = re.fullmatch(r"([-+0-9.eE]+?)(meg|[fpnumk])?", text.strip(), re.I)
    return float(f"{float(m.group(1)) * SCALE.get((m.group(2) or '').lower(), 1.0):.15g}")

def work_out(text, scope):
    text = text.strip()
    if "^" in text:
        raise ValueError(f"^ means power in SPICE and XOR in Python: {text}")
    return eval(text[1:-1], {}, scope) if text.startswith("{") else value(text)

def subcircuits(text):
    found, name = {}, None
    for line in text.splitlines():
        words = line.split()
        if not words or line.startswith("*"):
            continue
        if words[0].lower() == ".subckt":
            ports = [w for w in words[2:] if "=" not in w]
            defaults = dict(w.split("=", 1) for w in words[2:] if "=" in w)
            name = words[1]
            found[name] = {"ports": ports, "defaults": defaults, "lines": []}
        elif words[0].lower() == ".ends":
            name = None
        elif words[0].startswith("+"):
            raise ValueError(f"continuation lines are not read: {line}")
        elif name and words[0][0] in "Xx":
            found[name]["lines"].append(words)
        elif name:
            raise ValueError(f"only X lines are carried into the reference, not: {line}")
    return found

def expand(subs, name, nets, scope, path, out, mult=1):
    sub = subs[name]
    local = dict(scope)
    local.update({k: work_out(v, scope) for k, v in sub["defaults"].items()})
    local.update(nets["params"])
    net = lambda n: nets["map"].get(n, n if n == "0" else path + n)
    for words in sub["lines"]:
        given = dict(w.split("=", 1) for w in words[1:] if "=" in w)
        plain = [w for w in words[1:] if "=" not in w]
        child, nodes, inst = plain[-1], [net(n) for n in plain[:-1]], words[0][1:]
        params = {k: work_out(v, local) for k, v in given.items() if k != "mm_ok"}
        if child in MODELS:
            if mult * params.get("m", 1) != 1:
                params["m"] = int(mult * params.get("m", 1))
            out.append({"name": path + inst, "model": child, "nodes": nodes, "params": params})
        else:
            inner = mult * int(params.pop("m", 1))
            expand(subs, child, {"map": dict(zip(subs[child]["ports"], nodes)), "params": params}, local, path + inst + "_", out, inner)
    return out

def flatten(text, top, params):
    subs = subcircuits(text)
    return expand(subs, top, {"map": {p: p for p in subs[top]["ports"]}, "params": {}}, params, "", [])

def cdl(text, top, params):
    lines = [".subckt " + top + " " + " ".join(subcircuits(text)[top]["ports"])]
    for d in flatten(text, top, params):
        sizes = " ".join(f"{k}={v:.6g}" for k, v in d["params"].items())
        lines.append(f"{MODELS[d['model']]}{d['name']} {' '.join(d['nodes'])} {d['model']} {sizes}")
    return "\n".join(lines + [".ends"]) + "\n"

if __name__ == "__main__":
    top, sizes, *files = sys.argv[1:]
    params = {"mm": 0}
    for k, v in re.findall(r"(\w+)=(\S+)", " ".join(l for l in open(sizes).read().splitlines() if l.startswith(".param"))):
        params[k] = value(v)
    print(cdl("\n".join(open(f).read() for f in files), top, params), end="")
