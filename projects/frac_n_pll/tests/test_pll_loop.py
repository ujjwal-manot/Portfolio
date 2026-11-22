# Checks projects/frac_n_pll/model/pll_loop.py: passive loop-filter sizing against exact open-loop bandwidth and phase margin, closed-loop 10 GHz RMS jitter under 2 ps, and 3rd-order vs 1st-order MASH sigma-delta noise shaping.
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "model"))
from pll_loop import design_loop_filter, loop_metrics, closed_loop_jitter_s, mash111_sequence

def test_loop_filter_sizing_hits_bandwidth_phase_margin_and_lock_time():
    r1, c1, c2 = design_loop_filter(f_bw_hz=1.0e6, pm_deg=60.0, i_cp_a=200e-6, k_vco_hz_per_v=400e6, n_div=200.0)
    assert r1 > 0.0 and c1 > c2 > 0.0
    m = loop_metrics(r1, c1, c2, i_cp_a=200e-6, k_vco_hz_per_v=400e6, n_div=200.0)
    assert abs(m["f_bw_hz"] - 1.0e6) / 1.0e6 < 0.02
    assert abs(m["pm_deg"] - 60.0) < 0.5
    assert m["lock_time_s"] < 20e-6

def test_closed_loop_10ghz_jitter_clears_2ps_spec():
    r1, c1, c2 = design_loop_filter(f_bw_hz=1.0e6, pm_deg=60.0, i_cp_a=200e-6, k_vco_hz_per_v=400e6, n_div=200.0)
    j = closed_loop_jitter_s(
        r1, c1, c2,
        i_cp_a=200e-6, k_vco_hz_per_v=400e6, n_div=200.0, f_ref_hz=50e6,
        vco_l_1m_dbc=-110.0, cp_floor_dbc=-105.0, ref_floor_dbc=-145.0,
    )
    assert 50e-15 < j["rms_jitter_s"] < 2e-12

def test_mash111_exact_mean_bounds_and_third_order_noise_shaping():
    frac = int(round(0.371 * (1 << 20)))
    seq3 = mash111_sequence(frac, n_steps=16384, width=20, order=3)
    seq1 = mash111_sequence(frac, n_steps=16384, width=20, order=1)
    assert seq3.min() >= -3 and seq3.max() <= 4
    assert abs(float(seq3.mean()) - frac / float(1 << 20)) < 1e-3
    n = len(seq3)
    k = np.arange(n, dtype=float)
    win = 0.35875 - 0.48829 * np.cos(2.0 * np.pi * k / (n - 1)) + 0.14128 * np.cos(4.0 * np.pi * k / (n - 1)) - 0.01168 * np.cos(6.0 * np.pi * k / (n - 1))
    p3 = np.abs(np.fft.rfft((seq3 - seq3.mean()) * win)) ** 2
    p1 = np.abs(np.fft.rfft((seq1 - seq1.mean()) * win)) ** 2
    ratio_db = 10.0 * np.log10(float(p1[8:256].sum()) / max(1e-18, float(p3[8:256].sum())))
    slope_2oct_db = 10.0 * np.log10(float(p3[400:600].mean()) / max(1e-18, float(p3[100:150].mean())))
    assert ratio_db > 30.0
    assert slope_2oct_db > 30.0
