# Thick-oxide (3.3 V) layout on top of helpers/row_layout.py for the bandgap and the LDO: MOS units use IHP's nmosHV and pmosHV PCells under one ThickGateOx box per row, pnpMPA bipolars are drawn with the 1 x 2 um emitter the model simulates by default with emitter, base and collector each brought out by its own stack, a resistor longer than 40 um is drawn as straight segments in series (each joint its own net, so LVS combines them back into the schematic's one resistor instead of reading a bent PCell), and a MIM capacitor with m units (m a square number, each unit within IHP's 5625 um2 limit) becomes an n x n grid on one Metal5 bottom-plate sheet and top plates joined on TopMetal1; units() turns a flattened CDL into these row units and cap specs.
import math, re
import pya
from row_layout import Block, snap, VIA, STRAP, END

SEGMENT = 40.0
WMAX = 10.0
MIM_MAX = 5625.0

def size(words, k, default=None):
    found = [w for w in words if w.startswith(k + "=")]
    return float(found[0][len(k) + 1:]) * 1e6 if found else default

def units(cdl):
    rows = {"n": [], "p": []}
    caps = []
    for words in (l.split() for l in cdl.splitlines() if l[:1] in "MRCQ"):
        name = words[0]
        if name[0] == "M":
            d, g, s = words[1:4]
            ng, m = int(size(words, "ng", 1e6) / 1e6), int(size(words, "m", 1e6) / 1e6)
            split = math.ceil(size(words, "w") / ng / WMAX - 1e-9)
            kind = "p" if "pmos" in words[5] else "n"
            rows[kind].append({"kind": kind, "w": size(words, "w") / ng / split, "l": size(words, "l"), "ng": ng * m * split, "nets": {"d": d, "g": g, "s": s}})
        elif name[0] == "Q":
            c, b, e = words[1:4]
            rows["n"] += [{"kind": "q", "name": name, "nets": {"c": c, "b": b, "e": e}}] * int(size(words, "m", 1e6) / 1e6)
        elif name[0] == "R":
            a, b, model = words[1], words[2], words[4]
            l, w = size(words, "l"), size(words, "w")
            n = math.ceil(l / SEGMENT - 1e-9)
            joints = [a] + [f"{name}_{k}" for k in range(1, n)] + [b]
            rows["n"] += [{"kind": "r", "model": model, "w": w, "l": l / n, "nets": {"a": joints[k], "b": joints[k + 1]}} for k in range(n)]
        else:
            side, m = size(words, "w"), int(size(words, "m", 1e6) / 1e6)
            n = math.isqrt(m)
            if n * n != m or side * side > MIM_MAX:
                raise ValueError(f"{name}: a MIM must be at most {MIM_MAX} um2 and its m a square number, got {side} um and m={m}")
            caps.append({"top": words[1], "bottom": words[2], "n": n, "side": snap(side)})
    return rows["n"], rows["p"], caps

class HV(Block):
    def __init__(self, name):
        super().__init__(name)
        self.layer["tgo"] = self.ly.layer(44, 0)

    def place(self, name, params, left, y):
        return super().place(name + "HV" if name in ("nmos", "pmos") else name, params, left, y)

    def resistor(self, model, w, l, nets, left, y):
        cell, x = self.place(model, {"w": f"{snap(w):.3f}u", "l": f"{snap(l):.3f}u", "Calculate": "R"}, left, y)
        pads = sorted({round(b.bottom, 3): b for b in self.shapes(cell, "m1", x, y)}.values(), key=lambda b: b.bottom)
        self.stack(nets["a"], pads[0].center().x, pads[0].center().y, False)
        top = pads[-1]
        self.box("m1", top.left, top.bottom, top.center().x + 0.855, top.top)
        self.stack(nets["b"], top.center().x + 0.7, top.center().y, False)
        return cell.dbbox().moved(x, y)

    def pnp(self, nets, left, y):
        cell, x = self.place("pnpMPA", {"w": "1u", "l": "2u"}, left, y + 3.21)
        cy = y + 3.21
        base = min((b for b in self.shapes(cell, "m1", x, cy) if b.width() < 0.6 and 2.0 < b.height() < 3.0), key=lambda b: b.left)
        self.stack(nets["e"], x, cy, False)
        self.stack(nets["b"], base.center().x, cy, False)
        self.stack(nets["c"], x + 1.5, cy + 2.835, False)
        return cell.dbbox().moved(x, cy)

    def row(self, units, y, left=0.0):
        boxes = []
        for u in units:
            if u["kind"] == "r":
                b = self.resistor(u["model"], u["w"], u["l"], u["nets"], left, y)
            elif u["kind"] == "q":
                b = self.pnp(u["nets"], left, y)
            else:
                b = self.mos(u["kind"], u["w"], u["l"], u["ng"], u["nets"], left, y)
            boxes.append(b)
            left = b.right + 1.0
        mos = [b for b, u in zip(boxes, units) if u["kind"] in "np"]
        if mos:
            self.box("tgo", mos[0].left - 0.7, min(b.bottom for b in mos) - 0.7, mos[-1].right + 0.7, max(b.top for b in mos) + 0.7)
        return pya.DBox(boxes[0].left, min(b.bottom for b in boxes), boxes[-1].right, max(b.top for b in boxes))

    def cap_grid(self, cap, left, track_y):
        n, side = cap["n"], cap["side"]
        pitch = side + 1.65
        bottom = snap(track_y[cap["bottom"]] - 1.0)
        self.box("m5", left, bottom - 0.6, left + pitch * n - 0.45, bottom - 0.6 + pitch * n - 0.45)
        for i in range(n):
            for j in range(n):
                self.place("cmim", {"w": f"{side:.3f}u", "l": f"{side:.3f}u", "Calculate": "C"}, left + pitch * i, bottom + pitch * j)
        x0, x1 = left + 0.6, left + pitch * n - 1.05
        for k in range(3):
            self.square("via4", x0 + 1.0 + 0.5 * k, track_y[cap["bottom"]], VIA)
        for j in range(n):
            cy = bottom + 0.6 + pitch * j + side / 2
            self.box("topmetal1", x0 + 0.31, cy - 1.0, x1 + 4.0, cy + 1.0)
        ty = track_y[cap["top"]]
        top_bar = bottom + 0.6 + pitch * (n - 1) + side / 2 + 1.0
        self.box("topmetal1", x1 + 2.0, min(ty - 1.0, bottom), x1 + 4.0, max(top_bar, ty + 1.0))
        self.box("m5", x1 + 2.0, ty - 1.0, x1 + 4.0, ty + 1.0)
        self.square("topvia1", x1 + 3.0, ty, 0.42)
        for k in range(3):
            self.square("via4", x1 + 2.5 + 0.5 * k, ty, VIA)
        return {cap["bottom"]: x0 + 2.5, cap["top"]: x1 + 3.7}, x1 + 6.0

    def route(self, track_y, ports, extend={}):
        extend = dict(extend)
        for net in track_y:
            xs = {x for n, x, _, _ in self.terminals if n == net} | ({extend[net]} if net in extend else set())
            if len(xs) == 1:
                extend[net] = xs.pop() + 0.8
        super().route(track_y, ports, extend)
