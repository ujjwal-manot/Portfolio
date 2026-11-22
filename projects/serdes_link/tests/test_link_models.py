# Checks projects/serdes_link/model/link_models.py: PRBS7 maximal-length period and single-bit error detection, 1-tap sign-sign LMS DFE convergence vs flipped-sign divergence, bang-bang CDR frequency-offset tracking, and PAM4 Gray slicer vs swapped thresholds.
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "model"))
from link_models import prbs_generate, prbs_check, dfe_lms_run, bb_cdr_track, pam4_slice

def test_prbs7_has_period_127_and_detects_single_bit_error():
    bits = prbs_generate(order=7, length=300, seed=0x7F)
    assert bits[:127] == bits[127:254]
    assert bits[:63] != bits[63:126]
    assert prbs_check(bits, order=7) == 0
    bad = list(bits)
    bad[100] ^= 1
    assert prbs_check(bad, order=7) >= 1

def test_dfe_sign_sign_lms_converges_and_flipped_sign_diverges():
    bits = prbs_generate(order=7, length=512, seed=0x5A)
    tx = np.array([1.0 if b else -1.0 for b in bits], dtype=float)
    isi = np.zeros_like(tx)
    isi[0] = tx[0]
    isi[1:] = tx[1:] + 0.35 * tx[:-1]
    rx_int = np.round(isi * 64.0).astype(int)
    ok = dfe_lms_run(rx_int, target_amp=64, flip_sign=False)
    broken = dfe_lms_run(rx_int, target_amp=64, flip_sign=True)
    assert abs(ok["h1_final"] - round(0.35 * 64)) <= 3
    assert ok["tail_errors"] == 0
    assert abs(broken["h1_final"] - round(0.35 * 64)) > 20

def test_bang_bang_cdr_tracks_200ppm_frequency_offset():
    res = bb_cdr_track(n_ui=4000, ppm_offset=200.0, pi_bits=6)
    assert res["max_tail_phase_err_ui"] < 0.15
    assert res["wraps"] >= 1

def test_pam4_gray_slicer_clean_and_swapped_thresholds_fail():
    levels = np.array([-0.75, -0.25, 0.25, 0.75])
    syms = np.arange(64) % 4
    wave = levels[syms]
    want = [(0, 0), (0, 1), (1, 1), (1, 0)]
    got = pam4_slice(wave, thresholds=(-0.5, 0.0, 0.5))
    assert got == [want[s] for s in syms]
    bad = pam4_slice(wave, thresholds=(0.5, 0.0, -0.5))
    assert sum(a != b for a, b in zip(bad, got)) > 16
