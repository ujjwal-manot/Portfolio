# Measures the LDO pass device's own pins in ldo.gds (GDS from $GDS): for each Metal5 pin plate labelled vdd or vout, the plate's narrower side and the number of via1, via2, via3 and via4 cuts under it, then prints "own pins x2.xn=<fewest cuts at any level>,<narrowest plate in um>" for em_check.py: klayout -b -rd gds=ldo.gds -r layout/pins.py.
import pya
ly = pya.Layout()
ly.read(gds)
top = ly.top_cell()
cuts = {name: pya.Region(top.begin_shapes_rec(ly.layer(n, 0))) for name, n in (("via1", 19), ("via2", 29), ("via3", 49), ("via4", 66))}
texts = [(s.text.string, s.text.trans.disp) for s in top.shapes(ly.layer(67, 25)).each() if s.is_text()]
fewest, narrowest = None, None
for box in (s.box for s in top.shapes(ly.layer(67, 2)).each() if s.is_box()):
    net = next(t for t, p in texts if box.contains(p))
    counts = {k: r.interacting(pya.Region(box)).count() for k, r in cuts.items()}
    side = min(box.width(), box.height()) * ly.dbu
    print(f"{net} plate {box.width() * ly.dbu:.3f} x {box.height() * ly.dbu:.3f} um, cuts under it: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    fewest = min([fewest or 10 ** 9] + list(counts.values()))
    narrowest = min(narrowest or 1e9, side)
print(f"own pins x2.xn={fewest},{narrowest:.3f}")
