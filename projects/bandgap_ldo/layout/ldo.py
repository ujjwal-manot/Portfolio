# LDO layout: the flattened design netlist (NETLIST) laid out by hv_layout.py, thick-oxide NMOS units and the rhigh filter resistors (as series segments) in the lower row under a substrate ring, thick-oxide PMOS in the upper row inside an n-well ring, the four MIM capacitors as grids right of the rows, ports labelled on their Metal4 tracks, and the pass device's 2 mA brought out on its own pins (helpers/em_check.py found its single via stack and the 0.2 um vdd and vout tracks over IHP's electromigration limits): a via2 at every source and drain strip, Metal3 plates (the drain plate split around the source strap), via3 and via4 arrays and a 3 um Metal5 plate per side labelled vout and vdd, where the top level connects the rail; it prints the via count per level for em_check.py: HELPERS=helpers NETLIST=build/layout/ldo.cdl OUT=build/layout klayout -b -r layout/ldo.py (the CDL from spice_flatten.py)
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
import pya
from row_layout import VIA
big = next(u for u in nmos if u["kind"] == "n" and u["nets"]["d"] == "vdd" and u["nets"]["s"] == "vout")
inst = next(i for i in b.top.each_inst() if i.cell.basic_name() == "nmosHV" and int(i.cell.pcell_parameters_by_name()["ng"]) == big["ng"])
strips = sorted({round(r.left, 3): r for r in b.shapes(inst.cell, "m1", inst.dtrans.disp.x, 0.0) if r.height() > 0.25}.values(), key=lambda r: r.left)
h = max(r.top for r in strips)
strap = strips[0::2][len(strips[0::2]) // 2].center().x
counts = []
for index, net, ty in ((0, "vout", 0.3 * h), (1, "vdd", 0.7 * h)):
    xs = [r.center().x for r in strips[index::2]]
    up = [x for x in xs if index == 0 or abs(x - strap) > 0.6]
    for x in xs:
        b.square("m2", x, ty, 0.4)
        b.square("via2", x, ty, VIA)
    pieces = [(xs[0] - 0.2, xs[-1] + 0.2)] if index == 0 else [(xs[0] - 0.2, strap - 0.35), (strap + 0.35, xs[-1] + 0.2)]
    for x0, x1 in pieces:
        b.box("m3", x0, ty - 0.4, x1, ty + 0.4)
    b.box("m4", xs[0] - 0.2, ty - 0.4, xs[-1] + 0.2, ty + 0.4)
    for x in up:
        b.square("via3", x, ty, VIA)
        b.square("via4", x, ty, VIA)
    b.box("m5", xs[0] - 0.2, ty - 1.5, xs[-1] + 0.2, ty + 1.5)
    b.top.shapes(b.ly.layer(67, 2)).insert(pya.DBox(xs[0] - 0.2, ty - 1.5, xs[-1] + 0.2, ty + 1.5))
    b.top.shapes(b.ly.layer(67, 25)).insert(pya.DText(net, pya.DTrans((xs[0] + xs[-1]) / 2, ty)))
    counts.append(min(len(xs), len(up)))
    print(f"{net} pin over the pass device: {len(xs)} via2, {len(up)} via3, {len(up)} via4, Metal5 plate 3 um")
print(f"own pins x2.xn={min(counts)},3.0")
b.top.write(os.path.join(os.environ["OUT"], "ldo.gds"))
print("wrote ldo.gds", b.top.dbbox())
