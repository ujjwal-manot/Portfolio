# One digital LDO switch unit (dldo_unit.cir with its level shifter) laid out with helpers/hv_layout.py: thick-oxide NMOS in the lower row and thick-oxide PMOS (the two loads and the switch) in the upper row under ThickGateOx, the shifter's thin-oxide inverter beside each row outside it, a substrate ring on vss round the NMOS, an n-well ring on vin round the thick PMOS and a separate one on vdd round the thin PMOS, every net on its Metal4 track, and vin, out, vdd and vss each also on a TopMetal1 stripe across the whole cell so units placed side by side share them: HELPERS=helpers NETLIST=build/layout/dldo_unit.cdl OUT=build/layout klayout -b -r layout/dldo_unit.py
import os, sys
sys.path.insert(0, os.environ["HELPERS"])
import pya
from row_layout import Block, snap, VIA
from hv_layout import HV, units

STRIPES = ["vss", "vdd", "out", "vin"]
STRIPE_W, STRIPE_GAP = 2.0, 2.0
SIDE = 0.75

class Mixed(HV):
    lv = False

    def place(self, name, params, left, y):
        return Block.place(self, name, params, left, y) if self.lv else HV.place(self, name, params, left, y)

    def thin(self, u, left, y):
        old, self.lv = self.lv, True
        upper, nets = u["kind"] == "p", u["nets"]
        cell, x = self.place("pmos" if upper else "nmos", {"w": f"{snap(u['w']):.3f}u", "l": f"{snap(u['l']):.3f}u", "ng": "1"}, left + SIDE, y)
        self.lv = old
        strips = sorted({round(b.left, 3): b for b in self.shapes(cell, "m1", x, y) if b.height() > 0.25}.values(), key=lambda b: b.left)
        gate = self.shapes(cell, "poly", x, y)[0]
        h = max(b.top for b in strips) - y
        gx, gy = gate.center().x, y + h + 0.45
        self.box("poly", gate.left, y + h, gate.right, gy)
        self.box("poly", gx - 0.15, gy - 0.15, gx + 0.15, gy + 0.15)
        self.square("cont", gx, gy, 0.16)
        self.box("m1", gx - 0.15, gy - 0.16, gx + 0.15, gy + 0.16)
        self.stack(nets["g"], gx, gy, upper)
        ty = y + h / 2
        for side, s, dx in (("s", strips[0], -SIDE), ("d", strips[-1], SIDE)):
            sx = s.center().x + dx
            self.box("m1", min(sx, s.center().x) - 0.145, ty - 0.145, max(sx, s.center().x) + 0.145, ty + 0.145)
            self.stack(nets[side], sx, ty, upper)
        return pya.DBox(left, y + min(0, cell.dbbox().bottom), x + cell.dbbox().right + SIDE + 0.2, gy + 0.3)

def build(cdl, name, ports):
    nmos, pmos, _ = units(cdl)
    model = {l.split()[0][1:]: l.split()[5] for l in cdl.splitlines() if l[:1] == "M"}
    thick = lambda rows: [u for u in rows if "_hv_" in u["model"]]
    for rows, kind in ((nmos, "nmos"), (pmos, "pmos")):
        names = [n for n, m in model.items() if kind in m]
        for u, n in zip(rows, names):
            u["model"] = model[n]
    b = Mixed(name)
    nrow = b.row(thick(nmos), 0.0)
    lvn = [b.thin(u, nrow.right + 2.0, 0.0) for u in nmos if "_lv_" in u["model"]]
    narea = nrow + lvn[0]
    nring = b.ring("psub", narea, "vss", False, True)
    nets = list(dict.fromkeys(["vss"] + [u["nets"][k] for u in nmos + pmos for k in u["nets"]] + ["vdd", "vin"]))
    track_y = b.tracks(nets, nring.top + 1.0)
    y = max(track_y.values()) + 1.0 + 2.31
    prow = b.row(thick(pmos), y)
    pring = b.ring("nwell", prow, "vin", True, False)
    b.box("nwell", pring.left - 0.5, pring.bottom - 0.5, pring.right + 0.5, pring.top + 0.5)
    lvp = [b.thin(u, pring.right + 0.5 + 1.8 + 0.5 + 1.5, y) for u in pmos if "_lv_" in u["model"]]
    lring = b.ring("nwell", lvp[0], "vdd", True, False)
    b.box("nwell", lring.left - 0.5, lring.bottom - 0.5, lring.right + 0.5, lring.top + 0.5)
    right = max(nring.right, lring.right) + 1.0
    extend = {}
    for k, net in enumerate(STRIPES):
        x = snap(right + 1.0 + 1.5 * k)
        extend[net] = x + 0.21
    b.route(track_y, ports, extend)
    left = min(nring.left, pring.left) - 1.0
    width = snap(extend[STRIPES[-1]] + 1.5)
    for k, net in enumerate(STRIPES):
        x, ty = extend[net] - 0.21, track_y[net]
        sy = snap(nring.bottom + STRIPE_W / 2 + (STRIPE_W + STRIPE_GAP) * k)
        b.box("topmetal1", left, sy - STRIPE_W / 2, width, sy + STRIPE_W / 2)
        for d in (-0.21, 0.21):
            b.square("via4", x + d, ty, VIA)
        b.box("m5", x - 0.4, min(ty, sy) - 0.45, x + 0.4, max(ty, sy) + 0.45)
        b.square("topvia1", x, sy, 0.42)
    return b, pya.DBox(left, nring.bottom, width, max(pring.top, lring.top)), track_y

if __name__ == "__main__":
    b, frame, _ = build(open(os.environ["NETLIST"]).read(), "dldo_unit", {"on", "out", "vin", "vdd", "vss"})
    b.top.write(os.path.join(os.environ["OUT"], "dldo_unit.gds"))
    print("wrote dldo_unit.gds", frame)
