# Checks em_check: the probe list names every MOS of a two-level design by its ngspice path, a device or a net over its IHP limit fails and names itself, a missing or nan current fails, and a design inside every limit passes.
import math
import pytest
from em_check import probes, check

DESIGN = """.subckt pair a b vdd vss
XA a a vdd vdd sg13_hv_pmos w=8u l=8u ng=2
XB b a vdd vdd sg13_hv_pmos w=8u l=8u ng=2
XS b b vss vss stack w=2u l=4u m=2
.ends pair
.subckt stack d g s b w=1u l=1u
XA d g m b sg13_hv_nmos w={w} l={l/2}
XB m g s b sg13_hv_nmos w={w} l={l/2}
.ends stack
"""

def raw(currents):
    return "\n".join(f"@n.{path}[ids] = {value}" for path, value in currents.items())

def test_probe_paths_follow_the_hierarchy():
    found = probes(DESIGN, {}, {"x1": "pair"})
    assert found == [".save @n.x1.xa.nsg13_hv_pmos[ids]", ".save @n.x1.xb.nsg13_hv_pmos[ids]", ".save @n.x1.xs.xa.nsg13_hv_nmos[ids]", ".save @n.x1.xs.xb.nsg13_hv_nmos[ids]"]

def currents(top=10e-6, stack=20e-6):
    return {"x1.xa.nsg13_hv_pmos": top, "x1.xb.nsg13_hv_pmos": top, "x1.xs.xa.nsg13_hv_nmos": stack, "x1.xs.xb.nsg13_hv_nmos": stack}

def test_a_design_inside_every_limit_passes():
    ok, lines = check(raw(currents()), DESIGN, {}, {"x1": "pair"})
    assert ok, lines

def test_a_terminal_over_the_single_via_limit_fails_and_names_the_device():
    ok, lines = check(raw(currents(stack=0.5e-3)), DESIGN, {}, {"x1": "pair"})
    assert not ok
    assert any(l.startswith("FAIL x1.xs.xa") for l in lines)

def test_a_track_over_its_limit_fails_and_names_the_net():
    ok, lines = check(raw(currents(top=0.35e-3, stack=10e-6)), DESIGN, {}, {"x1": "pair"})
    assert not ok
    assert [l for l in lines if l.startswith("FAIL")] == [l for l in lines if l.startswith("FAIL x1 net vdd")]

@pytest.mark.parametrize("value", ["nan", None])
def test_a_missing_or_nan_current_fails(value):
    c = currents()
    if value is None:
        del c["x1.xs.xb.nsg13_hv_nmos"]
    else:
        c["x1.xs.xb.nsg13_hv_nmos"] = value
    ok, lines = check(raw(c), DESIGN, {}, {"x1": "pair"})
    assert not ok

def test_a_device_with_its_own_pins_uses_its_via_arrays_and_leaves_the_tracks():
    c = currents(top=0.35e-3, stack=10e-6)
    ok, lines = check(raw(c), DESIGN, {}, {"x1": "pair"}, {"x1.xb": (4, 1.0)})
    assert ok, lines
    assert any("x1.xb" in l and "own pins" in l for l in lines)
    c["x1.xb.nsg13_hv_pmos"] = 2.1e-3
    ok, lines = check(raw(c), DESIGN, {}, {"x1": "pair"}, {"x1.xb": (4, 1.0)})
    assert not ok
    assert any(l.startswith("FAIL x1.xb") for l in lines)
