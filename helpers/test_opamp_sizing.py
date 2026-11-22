# Checks opamp_sizing's resistor sizing (the value is kept and the length never goes below rhigh's 0.96 um minimum, which IHP's PCell refuses, widening the resistor instead) and that every size is drawable on the PCells' 0.01 um grid, widths per finger in 0.02 um steps so a device split in two units stays on it.
from opamp_sizing import resistor, drawable, RSH, REND

def value(w, l):
    return RSH * l / w + 2 * REND / w

def test_a_long_resistor_keeps_one_micron_width():
    w, l = resistor(20e3)
    assert w == 1e-6 and abs(value(w, l) - 20e3) < 1e-6

def test_a_short_resistor_is_widened_to_the_minimum_length():
    w, l = resistor(1000)
    assert abs(l - 0.96e-6) < 1e-12 and w > 1e-6 and abs(value(w, l) - 1000) < 1e-6

def test_sizes_land_on_the_drawing_grid():
    p = drawable({"w_in": 7.361e-6, "ng_in": 1, "w_pu": 16.97e-6, "ng_pu": 3, "l_rz": 0.7577e-6, "w_cc": 18.817e-6, "m_tail": 3})
    assert abs(p["w_in"] - 7.36e-6) < 1e-12 and abs(p["w_pu"] - 16.98e-6) < 1e-12 and abs(p["l_rz"] - 0.76e-6) < 1e-12
    assert abs(p["w_cc"] - 18.82e-6) < 1e-12 and p["m_tail"] == 3 and p["ng_pu"] == 3
