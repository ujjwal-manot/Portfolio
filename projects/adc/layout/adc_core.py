# ADC core layout (cap DAC with its switches, top-plate offset trim and calibration gating, plus the comparator): every MOS from the flattened design netlist goes into the NMOS or PMOS row of helpers/row_layout.py in netlist order, and the 256 unit MIM capacitors form a 16 x 16 common-centroid array, each unit paired with its mirror through the array centre and the pairs dealt out by distance from the centre in ruler order (every second pair to bit 7, every fourth to bit 6, and so on, the last pair to bit 0 and the dummy), the 64 minimum trim units fill four more rows above it the same way (every second mirrored pair to trim bit 6, every fourth to bit 5, and so on, the last pair to bits 1 and 0), each row of units with its bottom-plate tracks underneath, Metal2 trunks down to the row block's channel and the top plates joined on TopMetal1: NETLIST=adc_core.cdl OUT=build/layout klayout -b -r layout/adc_core.py (the CDL from spice_flatten.py)
import os, re, sys, math
sys.path.insert(0, os.environ.get("HELPERS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "helpers")))
import pya
from row_layout import Block, snap, VIA, STRAP, END

class Rows(Block):
    def pad(self, x, y, upper):
        for layer, size in (("via1", VIA), ("via2", VIA)) + ((("via3", VIA), ("via4", VIA)) if upper else ()):
            self.square(layer, x, y, size)
        for layer in ("m2",) + (("m3", "m4") if upper else ()):
            self.box(layer, x - 0.1, y - 0.375, x + 0.1, y + 0.375)

    def mos(self, kind, w, l, ng, nets, left, y):
        if ng > 1 or l >= 0.6:
            return super().mos(kind, w, l, ng, nets, left, y)
        cell, x = self.place("pmos" if kind == "p" else "nmos", {"w": f"{snap(w):.3f}u", "l": f"{snap(l):.3f}u", "ng": "1"}, left + 0.75, y)
        s, d = sorted({round(b.left, 3): b for b in self.shapes(cell, "m1", x, y) if b.height() > 0.25}.values(), key=lambda b: b.left)
        f = self.shapes(cell, "poly", x, y)[0]
        h = max(s.top, d.top) - y
        gy, fx = y + h + 0.45, f.center().x
        self.box("poly", f.left, y + h, f.right, gy)
        self.box("poly", fx - 0.15, gy - 0.15, fx + 0.15, gy + 0.15)
        self.square("cont", fx, gy, 0.16)
        self.box("m1", fx - 0.155, gy - 0.155, fx + 0.155, gy + 0.155)
        self.pad(fx, gy, kind == "p")
        self.terminals.append((nets["g"], snap(fx), snap(gy), kind == "p"))
        for strip, side, sign in ((s, "s", -1), (d, "d", 1)):
            tx, ty = snap(strip.center().x + 0.6 * sign), snap(strip.center().y)
            self.box("m1", min(tx, strip.center().x) - 0.15, ty - 0.155, max(tx, strip.center().x) + 0.15, ty + 0.155)
            self.pad(tx, ty, kind == "p")
            self.terminals.append((nets[side], tx, ty, kind == "p"))
        return pya.DBox(left, y + min(0, cell.dbbox().bottom), d.center().x + 0.85, gy + 0.6)

out = os.environ["OUT"]
devices = [l.split() for l in open(os.environ["NETLIST"]).read().splitlines() if l[:1] in "MC"]
size = lambda words, k: float(next(w for w in words if w.startswith(k + "="))[len(k) + 1:]) * 1e6

def unit(words):
    d, g, s, _ = words[1:5]
    ng = int(size(words, "ng") / 1e6) if any(w.startswith("ng=") for w in words) else 1
    return [{"kind": "p" if "pmos" in words[5] else "n", "w": size(words, "w") / ng, "l": size(words, "l"), "ng": 1, "nets": {"d": d, "g": g, "s": s}}] * ng

def row(kind):
    units = {w[0]: unit(w) for w in devices if w[0][0] == "M" and kind in w[5]}
    pair = [units.pop("MCMP_M1"), units.pop("MCMP_M2")] if kind == "nmos" else []
    centroid = [pair[0][0], pair[1][0], pair[1][1], pair[0][1]] if pair else []
    return [u for us in units.values() for u in us] + centroid

nmos, pmos = row("nmos"), row("pmos")
caps = [w for w in devices if w[0][0] == "C"]
side = max(size(c, "w") for c in caps)
trims = [c for c in caps if size(c, "w") < side]
caps = [c for c in caps if size(c, "w") == side]
tside = size(trims[0], "w")

b = Rows("adc_core")
nrow = b.row(nmos, 0.0)
nring = b.ring("psub", nrow, "vss", False, True)
nets = list(dict.fromkeys(["vss"] + [u["nets"][k] for u in nmos + pmos for k in "dgs"] + ["vdd", "top"] + sorted({c[2] for c in caps})))
track_y = b.tracks(nets, nring.top + 1.0)
prow = b.row(pmos, max(track_y.values()) + 1.0 + 2.31)
pring = b.ring("nwell", prow, "vdd", True, False)
b.box("nwell", pring.left - 0.5, pring.bottom - 0.5, pring.right + 0.5, pring.top + 0.5)

bottoms = sorted({c[2] for c in caps + trims})
N, PX, PY, TR = 16, 4.1, 9.0, 4
spots = sorted(range(N * N // 2), key=lambda k: (math.hypot(k % N - 7.5, k // N - 7.5), k))
owner = {}
by_bit = {}
for c in caps:
    by_bit.setdefault(c[2], []).append(c)
order = sorted(bottoms, key=lambda n: -len(by_bit[n]))
for q, k in enumerate(spots):
    tz = ((q + 1) & -(q + 1)).bit_length() - 1
    pick = [n for n in order if len(by_bit[n]) == 2 ** (7 - tz)] if tz < 7 else [n for n in order if len(by_bit[n]) == 1]
    first, second = (pick[0], pick[0]) if tz < 7 else (pick[0], pick[1])
    owner[k], owner[N * N - 1 - k] = first, second
tby_bit = {}
for c in trims:
    tby_bit.setdefault(c[2], []).append(c)
torder = sorted(tby_bit, key=lambda n: (-len(tby_bit[n]), n))
tspots = sorted(range(N * TR // 2), key=lambda k: (math.hypot(k % N - 7.5, k // N - 1.5), k))
for q, k in enumerate(tspots):
    tz = ((q + 1) & -(q + 1)).bit_length() - 1
    pick = [n for n in torder if len(tby_bit[n]) == 2 ** (5 - tz)] if tz < 5 else [n for n in torder if len(tby_bit[n]) == 1]
    first, second = (pick[0], pick[0]) if tz < 5 else (pick[0], pick[1])
    owner[N * N + k], owner[N * N + N * TR - 1 - k] = first, second
owner_rows = [{owner[j * N + i] for i in range(N)} for j in range(N + TR)]
trunk_x0 = max(nring.right, pring.right) + 3.0
trunk = {n: snap(trunk_x0 + 0.5 * i) for i, n in enumerate(bottoms)}
bar_x = max(trunk.values()) + 2.0
ax = bar_x + 1.64 + 3.0
ay = max(track_y.values()) + 8.0
row_track = lambda j, n: snap(ay + PY * j - 1.1 - 0.5 * bottoms.index(n))
for j in range(N + TR):
    reach = {}
    w = side if j < N else tside
    for i in range(N):
        n, x, y = owner[j * N + i], ax + PX * i, ay + PY * j
        b.place("cmim", {"w": f"{w:.3f}u", "l": f"{w:.3f}u", "Calculate": "C"}, x - 0.6, y - 0.6)
        cx, ty = x + w / 2, row_track(j, n)
        b.square("via4", cx, y - 0.4, VIA)
        b.box("m4", cx - STRAP / 2, ty - END, cx + STRAP / 2, y - 0.4 + END)
        b.square("via3", cx, ty, VIA)
        reach[n] = cx
    for n, cx in reach.items():
        ty = row_track(j, n)
        b.box("m3", trunk[n] - END, ty - STRAP / 2, cx + END, ty + STRAP / 2)
        b.square("via2", trunk[n], ty, VIA)
    lo, hi = (0.31, 1.95) if j < N else (tside / 2 - 0.82, tside / 2 + 0.82)
    b.box("topmetal1", bar_x, ay + PY * j + lo, ax + PX * (N - 1) + w / 2 + 0.82, ay + PY * j + hi)
for n, x in trunk.items():
    b.box("m2", x - STRAP / 2, track_y[n] - END, x + STRAP / 2, row_track(max(j for j in range(N + TR) if n in owner_rows[j]), n) + END)
    for layer, s in (("via2", VIA), ("m3", 0.4), ("via3", VIA)):
        b.square(layer, x, track_y[n], s)
b.box("topmetal1", bar_x, track_y["top"] - 1.0, bar_x + 1.64, ay + PY * (N + TR - 1) + tside / 2 + 0.82)
b.box("m5", bar_x, track_y["top"] - 0.5, bar_x + 1.64, track_y["top"] + 0.5)
b.square("topvia1", bar_x + 0.82, track_y["top"], 0.42)
b.square("via4", bar_x + 0.82, track_y["top"], VIA)
extend = dict(trunk, top=bar_x + 0.82)
b.route(track_y, {"top", "vin", "vcm", "vref_hi", "vref_lo", "samp", "cal", "cclk", "cmp", "cmpn", "vdd", "vss"} | {f"d{k}" for k in range(8)} | {f"t{k}" for k in range(7)}, extend)
b.top.write(os.path.join(out, "adc_core.gds"))
print("wrote", os.path.join(out, "adc_core.gds"), "cell", b.top.dbbox(), "bits", {n: sum(1 for v in owner.values() if v == n) for n in bottoms})
