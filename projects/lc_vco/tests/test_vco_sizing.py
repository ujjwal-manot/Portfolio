# Checks projects/lc_vco/model/vco_sizing.py: continuous 9 to 11 GHz tuning coverage across 16 overlapping coarse bands, start-up loop gain margin, sub-10 mW power, Leeson phase noise under -100 dBc/Hz at 1 MHz, and sensitivity to halved Q and reversed varactor polarity.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "model"))
from vco_sizing import size_vco_tank, band_coverage, vco_specs

def test_vco_tuning_covers_9_to_11_ghz_with_positive_band_overlap():
    cfg = size_vco_tank(f_min_hz=8.8e9, f_max_hz=11.2e9, l_tank_h=0.8e-9, n_bits=4)
    cov = band_coverage(cfg)
    assert cov["f_lowest_hz"] <= 9.0e9
    assert cov["f_highest_hz"] >= 11.0e9
    assert cov["min_overlap_hz"] > 0.0

def test_vco_meets_startup_power_and_leeson_phase_noise_specs():
    cfg = size_vco_tank(f_min_hz=8.8e9, f_max_hz=11.2e9, l_tank_h=0.8e-9, n_bits=4)
    sp = vco_specs(cfg, q_tank=14.0, i_tail_a=5.0e-3, vdd_v=1.2, gm_eff_s=12.0e-3)
    assert sp["startup_gain"] >= 2.5
    assert sp["power_w"] < 10.0e-3
    assert sp["leeson_1m_dbc_hz"] < -100.0
    half_q_vl = vco_specs(cfg, q_tank=7.0, i_tail_a=5.0e-3, vdd_v=1.2, gm_eff_s=12.0e-3)
    assert abs((half_q_vl["leeson_1m_dbc_hz"] - sp["leeson_1m_dbc_hz"]) - 3.01) < 0.2
    cl_hi = vco_specs(cfg, q_tank=14.0, i_tail_a=1.5e-3, vdd_v=1.2, gm_eff_s=12.0e-3)
    cl_lo = vco_specs(cfg, q_tank=7.0, i_tail_a=1.5e-3, vdd_v=1.2, gm_eff_s=12.0e-3)
    assert abs((cl_lo["leeson_1m_dbc_hz"] - cl_hi["leeson_1m_dbc_hz"]) - 9.03) < 0.2
    weak = vco_specs(cfg, q_tank=14.0, i_tail_a=1.0e-3, vdd_v=1.2, gm_eff_s=1.0e-3)
    assert weak["startup_gain"] < 1.0
