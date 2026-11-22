# Checks projects/serdes_frontend/model/frontend_sizing.py: CTLE 5 GHz Nyquist peaking vs misplaced zero, 3-tap FFE ISI cancellation vs flipped post-cursor tap sign, pad+ESD return loss S11 under -10 dB at 5 GHz, and CML TX swing and energy efficiency.
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "model"))
from frontend_sizing import ctle_peaking_db, ffe_equalize_pulse, return_loss_db, cml_tx_metrics

def test_ctle_achieves_nyquist_peaking_and_misplaced_zero_fails():
    pk = ctle_peaking_db(gm_s=10e-3, r_d_ohm=120.0, c_d_f=45e-15, r_s_ohm=450.0, c_s_f=320e-15, f_nyq_hz=5e9)
    assert 6.0 <= pk["peaking_db"] <= 13.0
    assert pk["gain_nyq_db"] > pk["gain_dc_db"] + 5.0
    bad = ctle_peaking_db(gm_s=10e-3, r_d_ohm=120.0, c_d_f=45e-15, r_s_ohm=450.0, c_s_f=15e-15, f_nyq_hz=5e9)
    assert bad["gain_nyq_db"] - bad["gain_dc_db"] < 2.0

def test_three_tap_ffe_cancels_isi_and_wrong_sign_worsens_it():
    pulse = np.array([0.08, 1.0, 0.32, 0.06, 0.01])
    ok = ffe_equalize_pulse(pulse, taps=(-0.08, 1.0, -0.30))
    bad = ffe_equalize_pulse(pulse, taps=(-0.08, 1.0, +0.30))
    assert ok["isi_ratio"] < 0.15
    assert bad["isi_ratio"] > 0.55

def test_pad_return_loss_and_cml_tx_efficiency():
    s11 = return_loss_db(f_hz=5e9, r_term_ohm=50.0, c_pad_f=120e-15)
    assert s11 < -10.0
    tx = cml_tx_metrics(i_tail_a=12e-3, r_load_ohm=50.0, vdd_v=1.2, data_rate_gbps=10.0)
    assert abs(tx["diff_swing_vpp"] - 0.6) < 0.05
    assert tx["pj_per_bit"] < 2.5
