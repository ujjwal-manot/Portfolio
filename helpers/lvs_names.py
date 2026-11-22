# Reads a KLayout LVS database and fails if any layout net named by a label (a port or a text-only name) was paired with a schematic net of another name, so a label on the wrong wire, which LVS itself ignores when the netlists still match, is caught; Magic names its nodes from the same labels, so this also holds for netlists built on those names: klayout -b -rd path=cell.lvsdb -r lvs_names.py
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
for line in wrong:
    print("FAIL", line)
print(f"{named} labelled nets, {len(wrong)} paired with another name")
sys.exit(1 if wrong or not named else 0)
