# Checks the opamp result reader names the worst corner for each spec, fails a corner that misses one or whose measurement failed, leaves swing unchecked at the 1.08 V supply (below the 1.16 V the opamp needs for it), counts Monte Carlo yield per spec and combined, and passes the two-pole model only when its numbers match the arithmetic.
import subprocess, sys
from pathlib import Path
from analog_results import corners, model, expected, montecarlo

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

def test_swing_is_not_required_at_the_lowest_supply(tmp_path):
    a = write(tmp_path, "corner_tt_27_nom.txt", GOOD)
    low = write(tmp_path, "corner_ss_125_lo.txt", GOOD.replace("out_high_v 1.14", "out_high_v 0.91"))
    assert corners([a, low])[0]
    assert not corners([a, write(tmp_path, "corner_ss_125_min.txt", GOOD.replace("out_high_v 1.14", "out_high_v 0.99"))])[0]

def test_montecarlo_yield_per_spec_and_combined(tmp_path):
    runs = [write(tmp_path, f"mc_{i}.txt", GOOD.replace("pm_deg 67", f"pm_deg {59 if i < 1 else 67}")) for i in range(100)]
    ok, yields, offsets = montecarlo(runs)
    assert yields["pm_deg"] == 0.99 and yields["combined"] == 0.99 and ok
    runs.append(write(tmp_path, "mc_100.txt", GOOD.replace("gbw_hz 2.8e7", "gbw_hz 1.9e7")))
    assert not montecarlo(runs)[0]

def test_each_failed_spec_gets_a_line_naming_it(tmp_path):
    bad = write(tmp_path, "corner_tt_27_nom.txt", GOOD.replace("pm_deg 67", "pm_deg 15").replace("a0_db 72", "a0_db 40"))
    out = subprocess.run([sys.executable, str(Path(__file__).parent / "analog_results.py"), "corners", str(bad)], capture_output=True, text=True).stdout
    assert "FAIL pm_deg" in out.splitlines() and "FAIL a0_db" in out.splitlines() and "FAIL gbw_hz" not in out.splitlines()
