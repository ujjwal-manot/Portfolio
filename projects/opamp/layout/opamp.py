# Opamp layout for helpers/row_layout.py: the input pair split into four units in ABBA order around the shared tail node and the NMOS mirror likewise (common centroid along the row), the folded PMOS pair as six alternating units, the 21-unit sink and every other multiplied device as one multi-finger device, the nulling rhigh at the NMOS row's end and the MIM Miller capacitor right of the rows; it writes the GDS to OUT and, for LVS, the design netlist with sizes.inc's values filled in to CDL (device lines as M, R and C, the form IHP's LVS reader takes): SIZES=build/sizes.inc OUT=build/layout klayout -b -r layout/opamp.py
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "helpers"))
from row_layout import Block, snap

here = os.path.dirname(os.path.abspath(__file__))
sizes = {k: float(v) for k, v in re.findall(r"\.param\s+(\w+)=(\S+)", open(os.environ["SIZES"]).read())}
s = lambda k: sizes[k] * 1e6
out = os.environ["OUT"]
os.makedirs(out, exist_ok=True)

def unit(kind, w, l, ng, d, g, src):
    return {"kind": kind, "w": w, "l": l, "ng": ng, "nets": {"d": d, "g": g, "s": src}}

nu = lambda ng, d, g: unit("n", s("w_nu"), s("l_nu"), ng, d, g, "vss")
pin, pbot = s("w_in") / 2, s("w_bot") / 2
nmos = [nu(int(sizes["m_ref"]), "ibias", "ibias"), nu(1, "vbp", "ibias"), nu(1, "vbpc", "ibias"), unit("n", s("w_bnc"), s("l_nu"), 1, "vbnc", "vbnc", "vss"),
        nu(int(sizes["m_tail"]), "t", "ibias"),
        unit("n", pin, s("l_in"), 1, "f1", "inn", "t"), unit("n", pin, s("l_in"), 1, "f2", "inp", "t"), unit("n", pin, s("l_in"), 1, "f2", "inp", "t"), unit("n", pin, s("l_in"), 1, "f1", "inn", "t"),
        unit("n", s("w_ncas"), s("l_ncas"), 1, "x", "vbnc", "n1"), unit("n", s("w_ncas"), s("l_ncas"), 1, "o1", "vbnc", "n2"),
        unit("n", pbot, s("l_bot"), 1, "n1", "x", "vss"), unit("n", pbot, s("l_bot"), 1, "n2", "x", "vss"), unit("n", pbot, s("l_bot"), 1, "n2", "x", "vss"), unit("n", pbot, s("l_bot"), 1, "n1", "x", "vss"),
        nu(int(sizes["m_sink"]), "out", "ibias"),
        {"kind": "r", "w": s("w_rz"), "l": s("l_rz"), "nets": {"a": "o1", "b": "cz"}}]
pu = lambda d, g: unit("p", s("w_pu") / 3, s("l_pu"), 3, d, g, "vdd")
fold = [pu("f1" if k % 2 == 0 else "f2", "vbp") for k in range(2 * int(sizes["m_fold"]))]
pmos = [pu("vbp", "vbp"), unit("p", s("w_bpc"), s("l_pu"), 1, "vbpc", "vbpc", "vdd"), pu("vbnc", "vbp")] + fold + [
        unit("p", s("w_pcas") / 3, s("l_pcas"), 3, "x", "vbpc", "f1"), unit("p", s("w_pcas") / 3, s("l_pcas"), 3, "o1", "vbpc", "f2"),
        unit("p", s("w_out") / 5, s("l_out"), 5, "out", "o1", "vdd")]
nets = ["vss", "ibias", "vbnc", "t", "inn", "inp", "f1", "f2", "n1", "n2", "x", "o1", "cz", "out", "vbp", "vbpc", "vdd"]

b = Block("opamp")
nrow = b.row(nmos, 0.0)
nring = b.ring("psub", nrow, "vss", False, True)
channel = nring.top + 1.0
track_y = b.tracks(nets, channel)
channel_top = max(track_y.values()) + 1.0
prow = b.row(pmos, channel_top + 2.0 + 0.31)
pring = b.ring("nwell", prow, "vdd", True, False)
b.box("nwell", pring.left - 0.5, pring.bottom - 0.5, pring.right + 0.5, pring.top + 0.5)
extend = b.capacitor(s("w_cc"), ("out", "cz"), max(nring.right, pring.right) + 3.0, track_y)
b.route(track_y, {"inp", "inn", "out", "vdd", "vss", "ibias"}, extend)
b.top.write(os.path.join(out, "opamp.gds"))

text = open(os.path.join(here, "..", "design", "opamp.cir")).read()
lines = [l for l in text.splitlines() if l.startswith((".subckt", ".ends", "X"))]
value = lambda m: f"{eval(m.group(1), {}, sizes):.6g}"
letter = {"sg13_lv_nmos": "M", "sg13_lv_pmos": "M", "rhigh": "R", "cap_cmim": "C"}
def device(l):
    words = l.split()
    model = next((w for w in words if w in letter), None)
    return letter[model] + l[1:] if l.startswith("X") and model else l
cdl = "\n".join(device(re.sub(r"\{([^}]+)\}", value, re.sub(r"\s*mm_ok=\{mm\}", "", l))) for l in lines)
open(os.path.join(out, "opamp.cdl"), "w").write(cdl + "\n")
print("wrote", os.path.join(out, "opamp.gds"), "cell", b.top.dbbox())
