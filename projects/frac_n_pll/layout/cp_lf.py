# Fractional-N PLL charge pump and passive loop filter layout for helpers/row_layout.py: NMOS current mirror XMR/XMPB/XMSNK, inverter NMOS XUPN, DOWN switch XSW_DN, and zero resistor XR1 (rhigh) in the psub-ringed row, PMOS mirror XMPR/XMSRC, inverter PMOS XUPP, and UP switch XSW_UP in the nwell-ringed row, and MIM loop-filter capacitors XC1/XC2 right of the rows; writes cp_lf.gds and cp_lf.cdl to OUT: SIZES=design/cp_lf_sizes.inc OUT=build/layout klayout -b -r layout/cp_lf.py
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "helpers"))
from row_layout import Block

here = os.path.dirname(os.path.abspath(__file__))
SCALE = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3}
parse_val = lambda v: float(v[:-1]) * SCALE[v[-1]] if v[-1] in SCALE else float(v)
sizes_path = os.environ.get("SIZES", os.path.join(here, "..", "design", "cp_lf_sizes.inc"))
sizes = {k: parse_val(v) for k, v in re.findall(r"(\w+)=([0-9.eE+-]+[fpnumk]?)", open(sizes_path).read())}
s = lambda k: sizes[k] * 1e6
out = os.environ.get("OUT", os.path.join(here, "..", "build", "layout"))
os.makedirs(out, exist_ok=True)

def unit(kind, w, l, ng, d, g, src):
    return {"kind": kind, "w": w, "l": l, "ng": ng, "nets": {"d": d, "g": g, "s": src}}

nmos = [
    unit("n", s("w_ref"), s("l_cp"), 1, "ibias", "ibias", "vss"),
    unit("n", s("w_ref"), s("l_cp"), 1, "vbp", "ibias", "vss"),
    unit("n", s("w_dn") / 10, s("l_cp"), 10, "snk_dn", "ibias", "vss"),
    unit("n", 1.0, 0.13, 1, "up_n", "up", "vss"),
    unit("n", s("w_sw_n") / 4, 0.13, 4, "vctrl", "dn", "snk_dn"),
    {"kind": "r", "w": s("w_r1"), "l": s("l_r1"), "nets": {"a": "vctrl", "b": "vz"}},
]
pmos = [
    unit("p", s("w_pref") / 2, s("l_cp"), 2, "vbp", "vbp", "vdd"),
    unit("p", s("w_up") / 20, s("l_cp"), 20, "src_up", "vbp", "vdd"),
    unit("p", 2.0, 0.13, 1, "up_n", "up", "vdd"),
    unit("p", s("w_sw_p") / 4, 0.13, 4, "vctrl", "up_n", "src_up"),
]
nets = ["vss", "ibias", "vbp", "snk_dn", "src_up", "up", "up_n", "dn", "vz", "vctrl", "vdd"]

b = Block("cp_lf")
nrow = b.row(nmos, 0.0)
nring = b.ring("psub", nrow, "vss", False, True)
track_y = b.tracks(nets, nring.top + 1.0)
prow = b.row(pmos, max(track_y.values()) + 3.31)
pring = b.ring("nwell", prow, "vdd", True, False)
b.box("nwell", pring.left - 0.5, pring.bottom - 0.5, pring.right + 0.5, pring.top + 0.5)
left, extend = max(nring.right, pring.right) + 3.0, {}
for side_key, top_net in (("w_c1", "vz"), ("w_c2", "vctrl")):
    side = s(side_key)
    reach = b.capacitor(side, ("vss", top_net), left, track_y)
    for net, x in reach.items():
        extend[net] = max(extend.get(net, x), x)
    left += side + 8.0
b.route(track_y, {"up", "dn", "vctrl", "ibias", "vdd", "vss"}, extend)
b.top.write(os.path.join(out, "cp_lf.gds"))

text = open(os.path.join(here, "..", "design", "cp_lf.cir")).read()
lines = [l for l in text.splitlines() if l.startswith((".subckt", ".ends", "X"))]
value = lambda m: f"{eval(m.group(1), {}, sizes):.6g}"
letter = {"sg13_lv_nmos": "M", "sg13_lv_pmos": "M", "rhigh": "R", "cap_cmim": "C"}
def device(l):
    words = l.split()
    model = next((w for w in words if w in letter), None)
    return letter[model] + l[1:] if l.startswith("X") and model else l
cdl = "\n".join(device(re.sub(r"\{([^}]+)\}", value, re.sub(r"\s*mm_ok=\{mm\}", "", l))) for l in lines)
open(os.path.join(out, "cp_lf.cdl"), "w").write(cdl + "\n")
print("wrote", os.path.join(out, "cp_lf.gds"), "cell", b.top.dbbox())
