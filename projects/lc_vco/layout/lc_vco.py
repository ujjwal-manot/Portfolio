# LC VCO layout for helpers/row_layout.py: cross-coupled NMOS pair XMN1/XMN2, tail mirror XMR/XMT, varactor units XV1, switched-cap NMOS switches and rhigh bias resistors in the lower psub-ringed row, cross-coupled PMOS pair XMP1/XMP2 in the upper nwell-ringed row, and the 4-bit MIM capacitor array right of the rows; writes lc_vco.gds and lc_vco.cdl to OUT: SIZES=design/lc_vco_sizes.inc OUT=build/layout klayout -b -r layout/lc_vco.py
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "helpers"))
from row_layout import Block

here = os.path.dirname(os.path.abspath(__file__))
SCALE = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3}
parse_val = lambda v: float(v[:-1]) * SCALE[v[-1]] if v[-1] in SCALE else float(v)
sizes_path = os.environ.get("SIZES", os.path.join(here, "..", "design", "lc_vco_sizes.inc"))
sizes = {k: parse_val(v) for k, v in re.findall(r"(\w+)=([0-9.eE+-]+[fpnumk]?)", open(sizes_path).read())}
s = lambda k: sizes[k] * 1e6
out = os.environ.get("OUT", os.path.join(here, "..", "build", "layout"))
os.makedirs(out, exist_ok=True)

def unit(kind, w, l, ng, d, g, src):
    return {"kind": kind, "w": w, "l": l, "ng": ng, "nets": {"d": d, "g": g, "s": src}}

ng_c, ng_t, nx_v = int(sizes["ng_core"]), int(sizes["ng_tail"]), max(1, int(sizes["nx_var"]) // 2)
nmos = [
    unit("n", s("w_ref"), s("l_tail"), 1, "ibias", "ibias", "vss"),
    unit("n", s("w_tail") / ng_t, s("l_tail"), ng_t, "tail", "ibias", "vss"),
    unit("n", s("w_nc") / ng_c, s("l_core"), ng_c, "outp", "outn", "tail"),
    unit("n", s("w_nc") / ng_c, s("l_core"), ng_c, "outn", "outp", "tail"),
    unit("n", s("w_var"), s("l_var"), nx_v, "vtune", "outp", "vtune"),
    unit("n", s("w_var"), s("l_var"), nx_v, "vtune", "outn", "vtune"),
]
for bit in range(4):
    nmos += [
        unit("n", s("w_sw") / 4, 0.13, 4, f"b{bit}_n1", f"sw{bit}", f"b{bit}_n2"),
        {"kind": "r", "w": 0.5, "l": 20.0, "nets": {"a": f"b{bit}_n1", "b": "vss"}},
        {"kind": "r", "w": 0.5, "l": 20.0, "nets": {"a": f"b{bit}_n2", "b": "vss"}},
    ]
pmos = [
    unit("p", s("w_pc") / ng_c, s("l_core"), ng_c, "outp", "outn", "vdd"),
    unit("p", s("w_pc") / ng_c, s("l_core"), ng_c, "outn", "outp", "vdd"),
]
nets = ["vss", "ibias", "tail", "vtune", "sw0", "sw1", "sw2", "sw3",
        "b0_n1", "b0_n2", "b1_n1", "b1_n2", "b2_n1", "b2_n2", "b3_n1", "b3_n2",
        "outp", "outn", "vdd"]

b = Block("lc_vco")
nrow = b.row(nmos, 0.0)
nring = b.ring("psub", nrow, "vss", False, True)
track_y = b.tracks(nets, nring.top + 1.0)
prow = b.row(pmos, max(track_y.values()) + 3.31)
pring = b.ring("nwell", prow, "vdd", True, False)
b.box("nwell", pring.left - 0.5, pring.bottom - 0.5, pring.right + 0.5, pring.top + 0.5)
left, extend = max(nring.right, pring.right) + 3.0, {}
for bit in range(4):
    side = s(f"w_c{bit}")
    for plate_net, node_net in (("outp", f"b{bit}_n1"), ("outn", f"b{bit}_n2")):
        reach = b.capacitor(side, (plate_net, node_net), left, track_y)
        for net, x in reach.items():
            extend[net] = max(extend.get(net, x), x)
        left += side + 8.0
b.route(track_y, {"outp", "outn", "vtune", "sw3", "sw2", "sw1", "sw0", "ibias", "vdd", "vss"}, extend)
b.top.write(os.path.join(out, "lc_vco.gds"))

text = open(os.path.join(here, "..", "design", "lc_vco.cir")).read()
lines = [l for l in text.splitlines() if l.startswith((".subckt", ".ends", "X", "L", "R"))]
env = {"w": 4e-6, **sizes}
value = lambda m: f"{eval(m.group(1), {}, env):.6g}"
letter = {"sg13_lv_nmos": "M", "sg13_lv_pmos": "M", "rhigh": "R", "cap_cmim": "C", "sg13_hv_svaricap": "C"}
def device(l):
    words = l.split()
    model = next((w for w in words if w in letter), None)
    return letter[model] + l[1:] if l.startswith("X") and model else l
cdl = "\n".join(device(re.sub(r"\{([^}]+)\}", value, re.sub(r"\s*mm_ok=\{mm\}", "", l))) for l in lines)
open(os.path.join(out, "lc_vco.cdl"), "w").write(cdl + "\n")
print("wrote", os.path.join(out, "lc_vco.gds"), "cell", b.top.dbbox())
