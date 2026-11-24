# Checks helpers/lvs_names.py against tiny in-memory LVS net-pair fixtures: matching case-insensitive labels pass, swapped or unpaired labels fail, missing required names fail, and an unlabelled layout fails.
import runpy, sys, types
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "lvs_names.py"

class FakeNet:
    def __init__(self, name):
        self.name = name

class FakePair:
    def __init__(self, layout, schematic):
        self._l = None if layout is None else FakeNet(layout)
        self._s = None if schematic is None else FakeNet(schematic)
    def first(self):
        return self._l
    def second(self):
        return self._s

def run_lvs_names(pairs, monkeypatch, capsys, names=None):
    class FakeXref:
        def each_circuit_pair(self):
            return ["top"]
        def each_net_pair(self, circuit):
            return [FakePair(l, s) for l, s in pairs]
    class FakeLvs:
        def read(self, p):
            self.path = p
        def xref(self):
            return FakeXref()
    fake_pya = types.SimpleNamespace(LayoutVsSchematic=FakeLvs)
    monkeypatch.setitem(sys.modules, "pya", fake_pya)
    init = {"path": "dummy.lvsdb"}
    if names is not None:
        init["names"] = names
    try:
        runpy.run_path(str(SCRIPT), init_globals=init)
        code = 0
    except SystemExit as e:
        code = e.code
    return code, capsys.readouterr().out

def test_matching_labels_and_internal_nets_pass(monkeypatch, capsys):
    code, out = run_lvs_names([("VDD", "vdd"), ("$1", "n1"), ("a", "a"), ("e8", "e8")], monkeypatch, capsys, names="a,e8")
    assert code == 0 and "3 labelled nets, 0 problems" in out

def test_mismatched_label_fails(monkeypatch, capsys):
    code, out = run_lvs_names([("vdd", "vss"), ("out", "out")], monkeypatch, capsys)
    assert code == 1 and "FAIL layout net vdd paired with schematic net vss" in out

def test_missing_required_name_fails(monkeypatch, capsys):
    code, out = run_lvs_names([("a", "a"), ("e3", "e3")], monkeypatch, capsys, names="a,e8,e3")
    assert code == 1 and "FAIL label e8 names no layout net" in out

def test_unlabelled_layout_fails(monkeypatch, capsys):
    code, out = run_lvs_names([("$1", "n1"), ("", "n2")], monkeypatch, capsys)
    assert code == 1 and "0 labelled nets, 0 problems" in out
