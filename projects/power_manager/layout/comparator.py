# Window comparator layout (the ADC's StrongARM latch with power_manager's sizes, flattened by spice_flatten.py) on helpers/row_layout.py: the NMOS row and the PMOS row are each placed mirror-symmetric about the input pair and the tail (inverter, latch NOR, cross-coupled device, input device on one side, their twins in reverse on the other), the 2 um input pair through row_layout's multi-finger drawing and every 0.13 um device through dldo_unit.py's thin-device drawing, a substrate ring on vss and an n-well ring on vdd, every net on its Metal4 track: HELPERS=helpers NETLIST=build/layout/comparator.cdl OUT=build/layout klayout -b -r layout/comparator.py
import os, sys
sys.path.insert(0, os.environ["HELPERS"])
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hv_layout import units
from dldo_unit import Mixed

NMOS = ["MIN_N", "MLN_NA", "MLN_NB", "MM3", "MM1", "MMT", "MM2", "MM4", "MLP_NB", "MLP_NA", "MIP_N"]
PMOS = ["MIN_P", "MLN_PA", "MLN_PB", "MR1", "MR3", "MM5", "MM6", "MR4", "MR2", "MLP_PB", "MLP_PA", "MIP_P"]

def row(b, found, order, y):
    left, boxes = 0.0, []
    for name in order:
        u = found[name]
        box = b.thin(u, left, y) if u["ng"] == 1 and u["l"] < 0.2 else b.mos(u["kind"], u["w"], u["l"], u["ng"], u["nets"], left, y)
        boxes.append(box)
        left = box.right + 1.0
    for box in boxes[1:]:
        boxes[0] += box
    return boxes[0]

cdl = open(os.environ["NETLIST"]).read()
nmos, pmos, _ = units(cdl)
lines = [l.split() for l in cdl.splitlines() if l[:1] == "M"]
found = dict(zip([w[0] for w in lines if "nmos" in w[5]] + [w[0] for w in lines if "pmos" in w[5]], nmos + pmos))
b = Mixed("comparator")
b.lv = True
nrow = row(b, found, NMOS, 0.0)
nring = b.ring("psub", nrow, "vss", False, True)
nets = list(dict.fromkeys(["vss", "inp", "inn", "t", "dn", "dp", "an", "ap", "bn", "bp", "clk", "outp", "outn", "LN_m", "LP_m", "vdd"]))
track_y = b.tracks(nets, nring.top + 1.0)
prow = row(b, found, PMOS, max(track_y.values()) + 1.0 + 2.31)
pring = b.ring("nwell", prow, "vdd", True, False)
b.box("nwell", pring.left - 0.5, pring.bottom - 0.5, pring.right + 0.5, pring.top + 0.5)
b.route(track_y, {"inp", "inn", "clk", "outp", "outn", "vdd", "vss"})
b.top.write(os.path.join(os.environ["OUT"], "comparator.gds"))
print("wrote comparator.gds", b.top.dbbox())
