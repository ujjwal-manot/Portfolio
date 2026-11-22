# Bandgap layout: the flattened design netlist (NETLIST) laid out by hv_layout.py, thick-oxide NMOS (amplifier loads, start-up and the trim switches and inverters) then the rppd resistors (R2 as series segments, the trim ladder as its fifteen 2 um units) in the lower row under a substrate ring, the pnpMPA bipolars beside it outside that ring (IHP's LVS finds a pnp by the hole in its own substrate-tie ring), the 1x emitter (Q1) in the middle of the eight 8x units (four each side, a common centroid along the row) and Q3 after them, thick-oxide PMOS in the upper row inside an n-well ring, the compensation MIM right of the rows, ports labelled on their Metal4 tracks, and the pnp emitter nets (a, e8, e3) named by text alone, so Magic, whose IHP rules extract no pnp, names those nodes for the post-layout netlist: HELPERS=helpers NETLIST=build/layout/bandgap.cdl OUT=build/layout klayout -b -r layout/bandgap.py (the CDL from spice_flatten.py)
import os, sys
import pya
sys.path.insert(0, os.environ["HELPERS"])
from hv_layout import HV, units

nmos, pmos, caps = units(open(os.environ["NETLIST"]).read())
q8 = [u for u in nmos if u["kind"] == "q" and u["name"] == "QQ8"]
bipolar = q8[:4] + [u for u in nmos if u["kind"] == "q" and u["name"] == "QQ1"] + q8[4:] + [u for u in nmos if u["kind"] == "q" and u["name"] not in ("QQ1", "QQ8")]
b = HV("bandgap")
nrow = b.row([u for u in nmos if u["kind"] in "np"] + [u for u in nmos if u["kind"] == "r"], 0.0)
nring = b.ring("psub", nrow, "vss", False, True)
qrow = b.row(bipolar, 0.0, nring.right + 2.0)
names = [u["nets"][k] for u in nmos + pmos for k in u["nets"]] + [c[k] for c in caps for k in ("top", "bottom")]
nets = list(dict.fromkeys(["vss"] + names + ["vdd"]))
track_y = b.tracks(nets, nring.top + 1.0)
prow = b.row(pmos, max(track_y.values()) + 1.0 + 2.31)
pring = b.ring("nwell", prow, "vdd", True, False)
b.box("nwell", pring.left - 0.5, pring.bottom - 0.5, pring.right + 0.5, pring.top + 0.5)
left, extend = max(qrow.right, pring.right) + 3.0, {}
for cap in caps:
    reach, left = b.cap_grid(cap, left, track_y)
    for net, x in reach.items():
        extend[net] = max(extend.get(net, x), x)
b.route(track_y, {"vref", "vg", "vdd", "vss", "trim3", "trim2", "trim1", "trim0"}, extend)
for net in ("a", "e8", "e3"):
    x = min(x for n, x, _, _ in b.terminals if n == net)
    b.top.shapes(b.layer["m4text"]).insert(pya.DText(net, pya.DTrans(x, track_y[net])))
b.top.write(os.path.join(os.environ["OUT"], "bandgap.gds"))
print("wrote bandgap.gds", b.top.dbbox())
