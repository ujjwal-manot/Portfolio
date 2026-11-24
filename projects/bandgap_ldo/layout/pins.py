# Measures the LDO pass device's own pins in a GDS ($gds): it extracts the connectivity from Metal1 up to Metal5 and, for each Metal5 pin plate labelled vdd or vout, counts the via1, via2, via3 and via4 cuts that belong to that plate's own net and lie under the plate, and the plate's narrower side, then prints "own pins x2.xn=<fewest cuts at any via level>,<narrowest plate in um>" for em_check.py: klayout -b -rd gds=ldo.gds -r layout/pins.py.
import pya
ly = pya.Layout()
ly.read(gds)
top = ly.top_cell()
l2n = pya.LayoutToNetlist(pya.RecursiveShapeIterator(ly, top, []))
names = ["m1", "via1", "m2", "via2", "m3", "via3", "m4", "via4", "m5"]
numbers = {"m1": 8, "via1": 19, "m2": 10, "via2": 29, "m3": 30, "via3": 49, "m4": 50, "via4": 66, "m5": 67}
layer = {n: l2n.make_layer(ly.layer(numbers[n], 0), n) for n in names}
for n in names:
    l2n.connect(layer[n])
for a, b in zip(names, names[1:]):
    l2n.connect(layer[a], layer[b])
l2n.extract_netlist()
texts = [(s.text.string, s.text.trans.disp) for s in top.shapes(ly.layer(67, 25)).each() if s.is_text()]
fewest, narrowest = None, None
for box in (s.box for s in top.shapes(ly.layer(67, 2)).each() if s.is_box()):
    label, point = next((t, p) for t, p in texts if box.contains(p))
    probe = l2n.probe_net(layer["m5"], pya.DPoint(point.x * ly.dbu, point.y * ly.dbu))
    under = pya.Region(box)
    counts = {v: (l2n.shapes_of_net(probe, layer[v], True).merged() & under).count() for v in ("via1", "via2", "via3", "via4")}
    side = min(box.width(), box.height()) * ly.dbu
    print(f"{label} plate {box.width() * ly.dbu:.3f} x {box.height() * ly.dbu:.3f} um, its own net's cuts under it: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    fewest = min([fewest or 10 ** 9] + list(counts.values()))
    narrowest = min(narrowest or 1e9, side)
print(f"own pins x2.xn={fewest},{narrowest:.3f}")
