# Lays out an analog block on IHP SG13G2 from its device list: every MOS is an SG13_dev PCell (gate fingers joined by a poly bar with contacts, sources and drains joined by Metal2 bars), NMOS units sit in a row ringed by a substrate tie and PMOS units in a row inside an n-well ringed by an n-well tie, rhigh resistors join the NMOS row, and every terminal climbs by its own strap (Metal3 from the NMOS row, Metal5 from the PMOS row) to its net's Metal4 track in the channel between the rows; MIM capacitors sit right of the rows on two of the tracks, port names go on the tracks as Metal4 labels, and spacings come from IHP's DRC rule values (metal 0.16 to 0.21 um widths and spaces, 0.19 um vias with 0.05 um end enclosure); run inside klayout -b.
import math, os, sys, importlib
import pya

BASE = os.environ["PDK_ROOT"] + "/ihp-sg13g2/libs.tech/klayout/python"
sys.path += [BASE, BASE + "/pycell4klayout-api/source/python"]
importlib.import_module("sg13g2_pycell_lib")

LAYERS = {"poly": (5, 0), "cont": (6, 0), "m1": (8, 0), "via1": (19, 0), "m2": (10, 0), "via2": (29, 0), "m3": (30, 0), "via3": (49, 0),
          "m4": (50, 0), "m4pin": (50, 2), "m4text": (50, 25), "via4": (66, 0), "m5": (67, 0), "nwell": (31, 0), "topvia1": (125, 0), "topmetal1": (126, 0)}
GAP, RING, PITCH, VIA, STRAP, END = 1.0, 1.5, 0.5, 0.19, 0.2, 0.145

def snap(x):
    return round(x / 0.005) * 0.005

class Block:
    def __init__(self, name):
        self.ly = pya.Layout()
        self.ly.dbu = 0.001
        self.ly.technology_name = "sg13g2"
        self.top = self.ly.create_cell(name)
        self.layer = {k: self.ly.layer(*v) for k, v in LAYERS.items()}
        self.terminals = []

    def box(self, layer, x0, y0, x1, y1):
        self.top.shapes(self.layer[layer]).insert(pya.DBox(snap(min(x0, x1)), snap(min(y0, y1)), snap(max(x0, x1)), snap(max(y0, y1))))

    def square(self, layer, x, y, size):
        self.box(layer, x - size / 2, y - size / 2, x + size / 2, y + size / 2)

    def place(self, name, params, left, y):
        cell = self.ly.create_cell(name, "SG13_dev", params)
        x = snap(left - cell.dbbox().left)
        self.top.insert(pya.DCellInstArray(cell.cell_index(), pya.DTrans(x, snap(y))))
        return cell, x

    def shapes(self, cell, layer, x, y):
        li = self.ly.layer(*LAYERS[layer])
        return [it.shape().dbbox().transformed(it.dtrans()).moved(x, y) for it in cell.begin_shapes_rec(li).each()]

    def stack(self, net, x, y, upper):
        for layer, size in (("via1", VIA), ("m2", 0.4), ("via2", VIA)) + ((("m3", 0.4), ("via3", VIA), ("m4", 0.4), ("via4", VIA)) if upper else ()):
            self.square(layer, x, y, size)
        self.terminals.append((net, snap(x), snap(y), upper))

    def mos(self, kind, w, l, ng, nets, left, y):
        cell, x = self.place("pmos" if kind == "p" else "nmos", {"w": f"{snap(w * ng):.3f}u", "l": f"{snap(l):.3f}u", "ng": str(ng)}, left, y)
        strips = sorted({round(b.left, 3): b for b in self.shapes(cell, "m1", x, y) if b.height() > 0.25}.values(), key=lambda b: b.left)
        fingers = sorted({round(b.left, 3): b for b in self.shapes(cell, "poly", x, y)}.values(), key=lambda b: b.left)
        h = max(b.top for b in strips) - y
        for f in fingers:
            self.box("poly", f.left, y + h, f.right, y + h + 0.55)
            self.square("cont", f.center().x, y + h + 0.40, 0.16)
        self.box("poly", fingers[0].left, y + h + 0.25, fingers[-1].right, y + h + 0.55)
        self.box("m1", fingers[0].left, y + h + 0.27, fingers[-1].right, y + h + 0.53)
        self.stack(nets["g"], fingers[0].center().x, y + h + 0.40, kind == "p")
        for side, index in (("s", 0), ("d", 1)):
            group = strips[index::2]
            ty = y + (h / 2 if ng == 1 else h * (0.3 if side == "s" else 0.7))
            for s in group:
                self.square("m1", s.center().x, ty, 0.29)
            if ng == 1:
                self.stack(nets[side], group[0].center().x, ty, kind == "p")
                continue
            for s in group:
                self.square("via1", s.center().x, ty, VIA)
            self.box("m2", group[0].center().x - 0.2, ty - 0.15, group[-1].center().x + 0.2, ty + 0.15)
            mid = group[len(group) // 2].center().x
            self.square("m2", mid, ty, 0.4)
            for layer, size in (("via2", VIA),) + ((("m3", 0.4), ("via3", VIA), ("m4", 0.4), ("via4", VIA)) if kind == "p" else ()):
                self.square(layer, mid, ty, size)
            self.terminals.append((nets[side], snap(mid), snap(ty), kind == "p"))
        return pya.DBox(left, y + min(0, cell.dbbox().bottom), x + cell.dbbox().right, y + h + 0.75)

    def rhigh(self, w, l, nets, left, y):
        cell, x = self.place("rhigh", {"w": f"{snap(w):.3f}u", "l": f"{snap(l):.3f}u", "Calculate": "R"}, left, y)
        pads = sorted({round(b.bottom, 3): b for b in self.shapes(cell, "m1", x, y)}.values(), key=lambda b: b.bottom)
        self.stack(nets["a"], pads[0].left + 0.25, pads[0].center().y, False)
        self.stack(nets["b"], pads[-1].right - 0.25, pads[-1].center().y, False)
        return cell.dbbox().moved(x, y)

    def row(self, units, y):
        left, boxes = 0.0, []
        for u in units:
            b = self.rhigh(u["w"], u["l"], u["nets"], left, y) if u["kind"] == "r" else self.mos(u["kind"], u["w"], u["l"], u["ng"], u["nets"], left, y)
            boxes.append(b)
            left = b.right + GAP
        return pya.DBox(boxes[0].left, min(b.bottom for b in boxes), boxes[-1].right, max(b.top for b in boxes))

    def ring(self, kind, area, net, upper, tie_top):
        w, h = (math.ceil((v + 2 * RING) / 0.02 - 1e-9) * 0.02 for v in (area.width(), area.height()))
        cell = self.ly.create_cell("guard_ring", "SG13_dev", {"type": kind, "w": f"{w:.3f}u", "h": f"{h:.3f}u"})
        cx, cy = snap(area.center().x), snap(area.center().y)
        self.top.insert(pya.DCellInstArray(cell.cell_index(), pya.DTrans(cx, cy)))
        outer = pya.DBox(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
        edge = outer.top - 0.15 if tie_top else outer.bottom + 0.15
        self.stack(net, outer.left + 0.6, edge, upper)
        return outer

    def tracks(self, nets, channel_bottom):
        return {n: snap(channel_bottom + 0.5 + PITCH * i) for i, n in enumerate(nets)}

    def capacitor(self, side, nets, left, track_y):
        bottom, top_net = nets
        cell, x = self.place("cmim", {"w": f"{snap(side):.3f}u", "l": f"{snap(side):.3f}u", "Calculate": "C"}, left, track_y[bottom] - side / 2)
        y = snap(track_y[bottom] - side / 2)
        plate = cell.dbbox().moved(x, y)
        for k in range(3):
            self.square("via4", plate.left + 1.0 + 0.5 * k, track_y[bottom], VIA)
        top = self.shapes(cell, "topmetal1", x, y)[0]
        cy = top.center().y
        island = pya.DBox(plate.right + 2.0, min(cy, track_y[top_net]) - 1.0, plate.right + 4.0, max(cy, track_y[top_net]) + 1.0)
        self.box("topmetal1", top.right - 2.0, cy - 1.0, island.right, cy + 1.0)
        self.box("m5", island.left, island.bottom, island.right, island.top)
        self.square("topvia1", island.center().x, cy, 0.42)
        for k in range(3):
            self.square("via4", island.left + 0.5 + 0.5 * k, track_y[top_net], VIA)
        return {bottom: plate.left + 2.5, top_net: island.right - 0.3}

    def route(self, track_y, ports, extend={}):
        for net, x, y, upper in self.terminals:
            ty = track_y[net]
            if upper:
                self.box("m5", x - STRAP / 2, ty - END, x + STRAP / 2, y + END)
                self.square("via4", x, ty, VIA)
            else:
                self.box("m3", x - STRAP / 2, y - END, x + STRAP / 2, ty + END)
                self.square("via3", x, ty, VIA)
        for net, ty in track_y.items():
            xs = [x for n, x, _, _ in self.terminals if n == net] + ([extend[net]] if net in extend else [])
            self.box("m4", min(xs) - END, ty - STRAP / 2, max(xs) + END, ty + STRAP / 2)
            if net in ports:
                self.box("m4pin", min(xs) - END, ty - STRAP / 2, min(xs) + 0.3, ty + STRAP / 2)
                self.top.shapes(self.layer["m4text"]).insert(pya.DText(net, pya.DTrans(snap(min(xs)), ty)))
