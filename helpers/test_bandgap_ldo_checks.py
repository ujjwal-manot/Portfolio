# Checks bandgap_ldo_checks: the pex mode passes a clean extracted netlist and fails a diode line, an unknown device model, a capacitor across a MIM's plates and a resistor across an rppd's ends; the startup and load modes hold the LDO's start-up and rail limits and fail nan or missing values.
import pytest
from bandgap_ldo_checks import pex, startup, load

CLEAN = """* NGSPICE file created from x.ext
.subckt x_pex a b vss
X0 a b vss vss sg13_hv_nmos ad=0.3p pd=2u as=0.3p ps=2u w=1u l=1u
X1 a m1_2# vss rppd l=36.25u w=1u
X2 m1_2# b vss rppd l=36.25u w=1u
X3 b vss cap_cmim l=20u w=20u
C0 a b 0.1f
R0 a a.n1 12.5
.ends
"""

def test_a_clean_netlist_passes_and_counts_its_resistor_segments():
    ok, lines = pex(CLEAN)
    assert ok, lines
    assert "rppd w=1u l=36.25u: 2" in lines

@pytest.mark.parametrize("extra, shown", [("D0 a vss dpw 1p\n", "diode"), ("X9 a b vss mystery\n", "mystery"),
                                          ("C9 vss b 2f\n", "across the plates of X3"), ("R9 m1_2# a 5\n", "across the ends of X1")])
def test_a_suspect_line_fails_and_says_why(extra, shown):
    ok, lines = pex(CLEAN.replace(".ends", extra + ".ends"))
    assert not ok
    assert any(shown in l for l in lines if l.startswith("FAIL"))

def row(final=1.206, top=1.21, settle=50e-6):
    return f"ldo_startup ramp_s 1e-08 final_v {final} top_v {top} settle_s {settle}\n"

def test_startup_limits(tmp_path):
    good, high, nan = tmp_path / "a.txt", tmp_path / "b.txt", tmp_path / "c.txt"
    good.write_text(row())
    high.write_text(row(top=1.33))
    nan.write_text(row(settle="-NAN"))
    assert startup([str(good)])[0]
    assert not startup([str(high)])[0]
    assert not startup([str(nan)])[0]

def test_load_limits(tmp_path):
    good, low, empty = tmp_path / "a.txt", tmp_path / "b.txt", tmp_path / "c.txt"
    good.write_text("load min_v 1.17 max_v 1.25\n")
    low.write_text("load min_v 1.15 max_v 1.25\n")
    empty.write_text("load min_v 1.17\n")
    assert load([str(good)])[0]
    assert not load([str(low)])[0]
    assert not load([str(empty)])[0]

def test_clean_drops_only_the_lines_counted_twice():
    from bandgap_ldo_checks import clean
    text = CLEAN.replace(".ends", "C9 vss b 2f\n\nC10 a vss 3f\n.ends")
    out, dropped = clean(text)
    assert [l.split()[0] for l in dropped] == ["C9"]
    assert "C10 a vss 3f" in out and "C9 " not in out
    assert pex(out)[0]

def test_a_wrapper_around_its_own_subcircuit_and_a_spliced_pnp_pass():
    text = CLEAN.replace(".ends", "XQ1 vss vss a pnpMPA a=2e-12 p=6e-06\n.ends\n.subckt x a b vss\nX1 a b vss x_pex\n.ends")
    assert pex(text)[0], pex(text)[1]
