# Checks helpers/phase_noise.py: zero-crossing extraction, sinusoidal phase-modulation spur in dBc/Hz, integrated rms jitter recovery, and Leeson's formula at a 10 GHz LC VCO operating point.
import math, pytest
import numpy as np
from phase_noise import zero_crossings, jitter_metrics, phase_noise_dbc_hz, integrated_jitter_s, leeson_dbc_hz

def test_zero_crossings_and_period_jitter_of_clean_carrier():
    f0 = 10e9
    t = np.linspace(0.0, 200.5 / f0, 40001)
    v = np.sin(2.0 * math.pi * f0 * t)
    zc = zero_crossings(t, v, threshold=0.0)
    assert len(zc) >= 198
    jm = jitter_metrics(zc)
    assert abs(jm["f0_hz"] - f0) / f0 < 1e-4
    assert jm["period_jitter_s"] < 1e-14

def test_single_tone_phase_modulation_spur_and_integrated_jitter():
    f0 = 10e9
    fm = 10e6
    beta = 0.01
    n_cycles = 4096
    k = np.arange(n_cycles, dtype=float)
    crossings = k / f0 + (beta / (2.0 * math.pi * f0)) * np.sin(2.0 * math.pi * fm * k / f0)
    spec = phase_noise_dbc_hz(crossings)
    rms_j = integrated_jitter_s(spec["f_offset_hz"], spec["l_dbc_hz"], f0, f_min_hz=1e6, f_max_hz=100e6)
    expected_rms_j = (beta / math.sqrt(2.0)) / (2.0 * math.pi * f0)
    assert abs(rms_j - expected_rms_j) / expected_rms_j < 0.15

def test_leeson_formula_hand_check_at_10_ghz():
    k_b = 1.380649e-23
    f0, df, q, p_sig, f_noise, temp = 10e9, 1e6, 15.0, 1e-3, 2.0, 300.0
    expected = 10.0 * math.log10((2.0 * f_noise * k_b * temp / p_sig) * (1.0 + (f0 / (2.0 * q * df)) ** 2))
    got = leeson_dbc_hz(df, f0, q, p_sig, noise_factor=f_noise, temp_k=temp, f_corner_hz=0.0)
    assert abs(got - expected) < 1e-9 and -120.0 < got < -115.0

def test_rejects_non_positive_leeson_inputs():
    with pytest.raises(ValueError):
        leeson_dbc_hz(0.0, 10e9, 10.0, 1e-3)
