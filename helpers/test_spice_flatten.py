# Checks spice_flatten: nested subcircuits expand to device lines with joined names, ports map to the caller's nets, internal nets get the instance path, and size expressions are worked out from the global .param values, the subcircuit's defaults and the instance's overrides; a line it cannot carry into the reference (a non-X element, a continuation, a .param inside a subcircuit, a ^ in an expression) stops it.
import pytest
from spice_flatten import flatten, value

NETLIST = """
.subckt tgate a b on off vdd vss w=1u
XN a on b vss sg13_lv_nmos w={w} l={l_sw} mm_ok={mm}
XP a off b vdd sg13_lv_pmos w={2*w} l={l_sw} mm_ok={mm}
.ends tgate
.subckt pair x y en enb vdd vss
XT1 x mid en enb vdd vss tgate w={w_big}
XT2 mid y en enb vdd vss tgate
XC x y cap_cmim w={w_unit} l={w_unit} mm_ok={mm}
XQ vss vss x pnpMPA m=8
.ends pair
"""

def test_value_reads_spice_suffixes():
    assert value("2.26u") == 2.26e-6 and value("0.13u") == 0.13e-6 and value("4") == 4.0 and value("1e-6") == 1e-6

def test_nested_instances_flatten_with_mapped_nets_and_worked_out_sizes():
    devices = flatten(NETLIST, "pair", {"l_sw": 0.13e-6, "w_big": 2e-6, "w_unit": 2.26e-6, "mm": 0})
    got = {d["name"]: d for d in devices}
    assert set(got) == {"T1_N", "T1_P", "T2_N", "T2_P", "C", "Q"}
    assert got["Q"]["model"] == "pnpMPA" and got["Q"]["nodes"] == ["vss", "vss", "x"] and got["Q"]["params"]["m"] == 8
    assert got["T1_N"]["nodes"] == ["x", "en", "mid", "vss"]
    assert got["T1_P"]["params"]["w"] == 4e-6 and got["T2_P"]["params"]["w"] == 2e-6 and got["T2_N"]["params"]["l"] == 0.13e-6
    assert got["T2_N"]["nodes"] == ["mid", "en", "y", "vss"]
    assert got["C"]["model"] == "cap_cmim" and got["C"]["params"]["w"] == 2.26e-6 and "mm_ok" not in got["C"]["params"]

def test_internal_nets_of_two_instances_stay_apart():
    text = NETLIST + """
.subckt chain i o vdd vss
XA i n1 vdd vss vdd vss tgate
XB n1 o vdd vss vdd vss tgate
.ends chain
.subckt dinv y a vdd vss
XP y a vdd vdd sg13_lv_pmos w=1u l=0.13u
XN y a vss vss sg13_lv_nmos w=0.5u l=0.13u
.ends dinv
.subckt two y a vdd vss
X1 m a vdd vss dinv
X2 y m vdd vss dinv
.ends two
"""
    nets = {tuple(d["nodes"]) for d in flatten(text, "two", {"l_sw": 1e-7, "mm": 0})}
    assert ("m", "a", "vdd", "vdd") in nets and ("y", "m", "vdd", "vdd") in nets
    nets = {d["name"]: d["nodes"] for d in flatten(text, "chain", {"l_sw": 1e-7, "mm": 0})}
    assert nets["A_N"][2] == "n1" and nets["B_N"][0] == "n1"
    outer = text + """
.subckt top p q vdd vss
XU p q vdd vss chain
XV q p vdd vss chain
.ends top
"""
    nets = {d["name"]: d["nodes"] for d in flatten(outer, "top", {"l_sw": 1e-7, "mm": 0})}
    assert nets["U_A_N"][2] == "U_n1" and nets["V_A_N"][2] == "V_n1"

def test_a_multiplier_on_a_subcircuit_instance_reaches_its_devices():
    text = """
.subckt stack2 d g s b w=1u l=1u
XA d g m b sg13_hv_nmos w={w} l={l/2}
XB m g s b sg13_hv_nmos w={w} l={l/2}
.ends stack2
.subckt top y a vss
XS y a vss vss stack2 w=16u l=32u m=2
XT y a vss vss stack2 w=4u l=8u
.ends top
"""
    got = {d["name"]: d["params"] for d in flatten(text, "top", {})}
    assert got["S_A"] == {"w": 16e-6, "l": 16e-6, "m": 2} and got["S_B"]["m"] == 2 and "m" not in got["T_A"]

@pytest.mark.parametrize("line", ["R1 a b 1k", "C1 a b 1p", "M1 d g s b nmos", "V1 a 0 1", "+ w=1u", ".param k=2", "XA a b sg13_lv_nmos w={2^3} l=1u"])
def test_a_line_it_cannot_carry_into_the_reference_stops_it(line):
    text = f"""
.subckt top a b
XN a b a b sg13_lv_nmos w=1u l=1u
{line}
.ends top
"""
    with pytest.raises(ValueError):
        flatten(text, "top", {})
