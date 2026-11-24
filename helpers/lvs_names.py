# Reads a KLayout LVS database and fails if any layout net named by a label (a port or a text-only name) was paired with a schematic net of another name, so a label on the wrong wire, which LVS itself ignores when the netlists still match, is caught, and every name passed in names= must label a net; Magic names its nodes from the same labels, so this also holds for netlists built on those names: klayout -b -rd path=cell.lvsdb [-rd names=a,e8] -r lvs_names.py
import sys
import pya

db = pya.LayoutVsSchematic()
db.read(path)
xref = db.xref()
named, wrong = 0, []
for circuit in xref.each_circuit_pair():
    for pair in xref.each_net_pair(circuit):
        layout, schematic = pair.first(), pair.second()
        if layout is None or not layout.name or layout.name.startswith("$"):
            continue
        named += 1
        if schematic is None or schematic.name.lower() != layout.name.lower():
            wrong.append(f"layout net {layout.name} paired with schematic net {schematic.name if schematic else 'none'}")
want = [n for n in (names.split(",") if "names" in globals() else []) if n]
seen = {pair.first().name.lower() for circuit in xref.each_circuit_pair() for pair in xref.each_net_pair(circuit) if pair.first() is not None and pair.first().name}
wrong += [f"label {n} names no layout net" for n in want if n.lower() not in seen]
for line in wrong:
    print("FAIL", line)
print(f"{named} labelled nets, {len(wrong)} problems")
sys.exit(1 if wrong or not named else 0)
