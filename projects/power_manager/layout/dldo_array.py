# Digital LDO switch array layout: 128 copies of the dldo_unit cell from dldo_unit.py in 8 rows of 16, units abutted so their vin, out, vdd and vss TopMetal1 stripes run unbroken along each row and on to the left edge, where one 4 um TopMetal2 trunk per net (16 mA/um in the process spec, so up to 64 mA against the 43 mA of 128 units at 335 uA) joins the rows through two TopVia2 each; each unit's on input is named on<k> at its Metal4 track (the copy of the unit used here carries no on label of its own, so every on<k> net has one name): HELPERS=helpers NETLIST=build/layout/dldo_unit.cdl OUT=build/layout klayout -b -r layout/dldo_array.py
import os, sys
sys.path.insert(0, os.environ["HELPERS"])
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pya
from row_layout import snap
from dldo_unit import build, STRIPES, STRIPE_W, STRIPE_GAP

ROWS, COLS, TRUNK, TRUNK_GAP, ROW_GAP = 8, 16, 4.0, 5.0, 2.0
b, frame, track_y = build(open(os.environ["NETLIST"]).read(), "dldo_unit", {"out", "vin", "vdd", "vss"})
ly, unit = b.ly, b.top
top = ly.create_cell("dldo_array")
layer = lambda n, d: ly.layer(n, d)
tm1, tv2, tm2, tm2pin, tm2text = layer(126, 0), layer(133, 0), layer(134, 0), layer(134, 2), layer(134, 25)
m4, m4pin, m4text = layer(50, 0), layer(50, 2), layer(50, 25)
box = lambda l, x0, y0, x1, y1: top.shapes(l).insert(pya.DBox(snap(x0), snap(y0), snap(x1), snap(y1)))
on_x = min(x for n, x, _, _ in b.terminals if n == "on")
pitch_x, pitch_y = frame.width(), frame.height() + ROW_GAP
trunk_x = [frame.left - 2.0 - TRUNK / 2 - (TRUNK + TRUNK_GAP) * (len(STRIPES) - 1 - k) for k in range(len(STRIPES))]
edge = trunk_x[0] - TRUNK / 2 - 1.0
for r in range(ROWS):
    for c in range(COLS):
        dx, dy = pitch_x * c, pitch_y * r
        top.insert(pya.DCellInstArray(unit.cell_index(), pya.DTrans(snap(dx), snap(dy))))
        k = r * COLS + c
        x, y = on_x + dx, track_y["on"] + dy
        box(m4, x - 0.1, y - 0.1, x + 0.1, y + 0.1)
        box(m4pin, x - 0.1, y - 0.1, x + 0.1, y + 0.1)
        top.shapes(m4text).insert(pya.DText(f"on{k}", pya.DTrans(snap(x), snap(y))))
    for k, net in enumerate(STRIPES):
        sy = frame.bottom + STRIPE_W / 2 + (STRIPE_W + STRIPE_GAP) * k + pitch_y * r
        box(tm1, edge, sy - STRIPE_W / 2, frame.left + 0.01, sy + STRIPE_W / 2)
        for d in (-0.98, 0.98):
            box(tv2, trunk_x[k] + d - 0.45, sy - 0.45, trunk_x[k] + d + 0.45, sy + 0.45)
bottom, height = frame.bottom - 1.0, pitch_y * (ROWS - 1) + frame.height() + 2.0
for k, net in enumerate(STRIPES):
    box(tm2, trunk_x[k] - TRUNK / 2, bottom, trunk_x[k] + TRUNK / 2, bottom + height)
    box(tm2pin, trunk_x[k] - TRUNK / 2, bottom, trunk_x[k] + TRUNK / 2, bottom + 2.0)
    top.shapes(tm2text).insert(pya.DText(net, pya.DTrans(snap(trunk_x[k]), snap(bottom + 1.0))))
top.write(os.path.join(os.environ["OUT"], "dldo_array.gds"))
print("wrote dldo_array.gds", top.dbbox())
