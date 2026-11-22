# Checks the LDO result reader on made-up files: a corner fails on any missed limit (load and line regulation, quiescent current, the rail under 1.16 V on a 0.5 mA step, over 1.32 V after a 2 mA step or at start-up, phase margin under 45 deg at any load, supply rejection, start-up value and time), and the loop-gain measurement passes only when it reproduces the ideal two-pole loop's arithmetic.
import cmath, math
from ldo_results import corner, model, expected, summary

GOOD = """ldo_dc vout_v 1.2065 vout_2ma_v 1.2058 load_reg_v 0.0007 line_v_per_v 0.0044 iq_a 0.00016
psrr psrr_1k_db 47 psrr_1m_db 37
step_0p5m istep_a 0.0005 before_v 1.2065 dip_v 1.176 high_v 1.2062 peak_v 1.235
step_2m istep_a 0.002 before_v 1.2065 dip_v 1.14 high_v 1.2058 peak_v 1.27
loop_0 gain_db 46 fc_hz 3.8e6 pm_deg 47
loop_250u gain_db 46 fc_hz 4.5e6 pm_deg 64
ldo_startup ramp_s 1e-08 final_v 1.2063 top_v 1.2063 settle_s 5.7e-05
"""

def write(tmp_path, name, text):
    (tmp_path / name).write_text(text)
    return tmp_path / name

def test_a_good_corner_passes_and_each_limit_fails_it(tmp_path):
    assert corner(write(tmp_path, "tt.txt", GOOD))[0]
    for old, new in [("load_reg_v 0.0007", "load_reg_v 0.006"), ("iq_a 0.00016", "iq_a 0.00021"), ("dip_v 1.176", "dip_v 1.15"),
                     ("peak_v 1.27", "peak_v 1.33"), ("pm_deg 47", "pm_deg 40"), ("psrr_1m_db 37", "psrr_1m_db 19"),
                     ("top_v 1.2063", "top_v 1.4"), ("settle_s 5.7e-05", "settle_s 3e-04")]:
        assert not corner(write(tmp_path, "bad.txt", GOOD.replace(old, new)))[0], new

def test_a_missing_run_fails(tmp_path):
    assert not corner(write(tmp_path, "tt.txt", GOOD.replace("psrr psrr_1k_db 47 psrr_1m_db 37\n", "")))[0]

def test_loop_measurement_must_match_the_ideal_loop(tmp_path):
    e = expected()
    assert abs(e["gain_db"] - 20 * math.log10(1000 * 10 / 10.1)) < 1e-9 and 50 < e["pm_deg"] < 55
    exact = write(tmp_path, "loop.txt", "loop " + " ".join(f"{k} {v}" for k, v in e.items()) + "\n")
    assert model(exact)[0]
    assert not model(write(tmp_path, "off.txt", exact.read_text().replace(f"pm_deg {e['pm_deg']}", f"pm_deg {e['pm_deg'] + 2}")))[0]

def test_current_limit_scales_with_absolute_temperature(tmp_path):
    hot = lambda iq: corner(write(tmp_path, "ldo_ff_3v6_125.txt", GOOD.replace("iq_a 0.00016", f"iq_a {iq}")))[0]
    assert hot(0.00026) and not hot(0.00027)
    assert not corner(write(tmp_path, "ldo_tt_3v3_27.txt", GOOD.replace("iq_a 0.00016", "iq_a 0.000205")))[0]
    assert corner(write(tmp_path, "ldo_tt_3v0_m40.txt", GOOD.replace("iq_a 0.00016", "iq_a 0.000195")))[0]
    assert not corner(write(tmp_path, "ldo_tt_3v0_m40.txt", GOOD.replace("iq_a 0.00016", "iq_a 0.000205")))[0]

def test_study_summary_takes_current_dip_and_no_load_margin(tmp_path):
    assert summary(write(tmp_path, "ldo_tt_3v3_27.txt", GOOD)) == (0.00016, 1.176, 47.0)
