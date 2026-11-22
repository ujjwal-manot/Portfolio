# CTLE layout for helpers/row_layout.py: differential NMOS input pair XM1/XM2, tail current mirror XMR/XT1/XT2, and degeneration/load resistors XRD1/XRD2/XRS in the psub-ringed row, with MIM peaking capacitor XCS right of the row and Metal4 port labels; writes ctle.gds and ctle.cdl to OUT: SIZES=design/ctle_sizes.inc OUT=build/layout klayout -b -r layout/ctle.py
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "helpers"))
from row_layout import Block

here = os.path.dirname(os.path.abspath(__file__))
SCALE = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3}
parse_val = lambda v: float(v[:-1]) * SCALE[v[-1]] if v[-1] in SCALE else float(v)
sizes_path = os.environ.get("SIZES", os.path.join(here, "..", "design", "ctle_sizes.inc"))
sizes = {k: parse_val(v) for k, v in re.findall(r"(\w+)=([0-9.eE+-]+[fpnumk]?)", open(sizes_path).read())}
s = lambda k: sizes[k] * 1e6
out = os.environ.get("OUT", os.path.join(here, "..", "build", "layout"))
os.makedirs(out, exist_ok=True)

def unit(kind, w, l, ng, d, g, src):
    return {"kind": kind, "w": w, "l": l, "ng": ng, "nets": {"d": d, "g": g, "s": src}}

nmos = [
    unit("n", s("w_ref"), 0.4, 1, "ibias", "ibias", "vss"),
    unit("n", s("w_tail") / 8, 0.4, 8, "s1", "ibias", "vss"),
    unit("n", s("w_in") / 8, 0.13, 8, "outn", "inp", "s1"),
    unit("n", s("w_in") / 8, 0.13, 8, "outp", "inn", "s2"),
    unit("n", s("w_tail") / 8, 0.4, 8, "s2", "ibias", "vss"),
    {"kind": "r", "w": s("w_rd"), "l": s("l_rd"), "nets": {"a": "vdd", "b": "outp"}},
    {"kind": "r", "w": s("w_rd"), "l": s("l_rd"), "nets": {"a": "vdd", "b": "outn"}},
    {"kind": "r", "w": s("w_rs"), "l": s("l_rs"), "nets": {"a": "s1", "b": "s2"}},
]
nets = ["vss", "ibias", "s1", "s2", "inp", "inn", "outn", "outp", "vdd"]

b = Block("ctle")
nrow = b.row(nmos, 0.0)
nring = b.ring("psub", nrow, "vss", False, True)
track_y = b.tracks(nets, nring.top + 1.0)
extend = b.capacitor(s("w_cs"), ("s1", "s2"), nring.right + 3.0, track_y)
b.route(track_y, {"inp", "inn", "outp", "outn", "ibias", "vdd", "vss"}, extend)
b.top.write(os.path.join(out, "ctle.gds"))

text = open(os.path.join(here, "..", "design", "ctle.cir")).read()
lines = [l for l in text.splitlines() if l.startswith((".subckt", ".ends", "X"))]
value = lambda m: f"{eval(m.group(1), {}, sizes):.6g}"
letter = {"sg13_lv_nmos": "M", "rppd": "R", "cap_cmim": "C", "diodevdd_2kv": "D", "diodevss_2kv": "D"}
def device(l):
    words = l.split()
    model = next((w for w in words if w in letter), None)
    return letter[model] + l[1:] if l.startswith("X") and model else l
cdl = "\n".join(device(re.sub(r"\{([^}]+)\}", value, re.sub(r"\s*mm_ok=\{mm\}", "", l))) for l in lines)
open(os.path.join(out, "ctle.cdl"), "w").write(cdl + "\n")
print("wrote", os.path.join(out, "ctle.gds"), "cell", b.top.dbbox())
