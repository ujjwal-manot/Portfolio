# Checks the opamp result reader names the worst corner for each spec, fails a corner that misses one or whose measurement failed, and passes the two-pole model only when its numbers match the arithmetic.
from analog_results import corners, model, expected

GOOD = ("loop a0_db 72 fc_hz 1.3e7 pm_deg 67 gbw_hz 2.8e7 ugf_hz 2.4e7\nstep supply_a 1.5e-4 rise_slew_v_per_s 2e7 fall_slew_v_per_s 1.7e7 rise_settle_s 6e-8 fall_settle_s 1.1e-7\n"
        "noise band_v_rms 1e-4 total_v_rms 3.4e-4 psrr_1k_db 47 psrr_1m_db 24\nswing out_low_v 0.04 out_high_v 1.14\n")

def write(tmp_path, name, text):
    (tmp_path / name).write_text(text)
    return tmp_path / name

def test_all_corners_pass_and_the_worst_is_named(tmp_path):
    a = write(tmp_path, "corner_tt_27_nom.txt", GOOD)
    b = write(tmp_path, "corner_ss_125_lo.txt", GOOD.replace("gbw_hz 2.8e7", "gbw_hz 2.1e7"))
    ok, rows = corners([a, b])
    assert ok and rows["gbw_hz"][:2] == (2.1e7, "ss_125_lo")

def test_a_missed_spec_or_failed_measurement_fails(tmp_path):
    a = write(tmp_path, "corner_tt_27_nom.txt", GOOD)
    assert not corners([a, write(tmp_path, "corner_ss_125_lo.txt", GOOD.replace("pm_deg 67", "pm_deg 55"))])[0]
    assert not corners([a, write(tmp_path, "corner_ff_m40_hi.txt", GOOD.replace("rise_settle_s 6e-8", "rise_settle_s -1.00005e-06"))])[0]
    assert not corners([a, write(tmp_path, "corner_fs_27_nom.txt", GOOD.replace("swing out_low_v 0.04 out_high_v 1.14\n", ""))])[0]

def test_two_pole_model_must_match_arithmetic(tmp_path):
    e = expected()
    exact = write(tmp_path, "model.txt", "loop " + " ".join(f"{k} {v}" for k, v in e.items()) + "\n")
    assert model(exact)[0]
    off = write(tmp_path, "off.txt", exact.read_text().replace(f"pm_deg {e['pm_deg']}", f"pm_deg {e['pm_deg'] + 3}"))
    assert not model(off)[0]
