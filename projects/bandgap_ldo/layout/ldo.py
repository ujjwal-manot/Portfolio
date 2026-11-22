# LDO layout: the flattened design netlist (NETLIST) laid out by hv_layout.py, thick-oxide NMOS units and the rhigh filter resistors (as series segments) in the lower row under a substrate ring, thick-oxide PMOS in the upper row inside an n-well ring, the four MIM capacitors as grids right of the rows, ports labelled on their Metal4 tracks: HELPERS=helpers NETLIST=build/layout/ldo.cdl OUT=build/layout klayout -b -r layout/ldo.py (the CDL from spice_flatten.py)
import os, sys
sys.path.insert(0, os.environ["HELPERS"])
from hv_layout import HV, units

nmos, pmos, caps = units(open(os.environ["NETLIST"]).read())
b = HV("ldo")
nrow = b.row([u for u in nmos if u["kind"] != "r"] + [u for u in nmos if u["kind"] == "r"], 0.0)
nring = b.ring("psub", nrow, "vss", False, True)
names = [u["nets"][k] for u in nmos + pmos for k in u["nets"]] + [c[k] for c in caps for k in ("top", "bottom")]
nets = list(dict.fromkeys(["vss"] + names + ["vdd"]))
track_y = b.tracks(nets, nring.top + 1.0)
prow = b.row(pmos, max(track_y.values()) + 1.0 + 2.31)
pring = b.ring("nwell", prow, "vdd", True, False)
b.box("nwell", pring.left - 0.5, pring.bottom - 0.5, pring.right + 0.5, pring.top + 0.5)
left, extend = max(nring.right, pring.right) + 3.0, {}
for cap in caps:
    reach, left = b.cap_grid(cap, left, track_y)
    for net, x in reach.items():
        extend[net] = max(extend.get(net, x), x)
b.route(track_y, {"vout", "fb", "vref", "vg", "vdd", "vss"}, extend)
b.top.write(os.path.join(os.environ["OUT"], "ldo.gds"))
print("wrote ldo.gds", b.top.dbbox())
