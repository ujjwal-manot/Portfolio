# Checks helpers/eye_diagram.py on deterministic NRZ and PAM4 bitstreams with known eye height, eye width, and crossing jitter.
import math, pytest
import numpy as np
from eye_diagram import fold_eye, eye_metrics

def make_wave(symbols, ui_s, samples_per_ui=64, rise_ui=0.1, jitter_ui=0.0):
    n = len(symbols) * samples_per_ui
    t = np.arange(n, dtype=float) * (ui_s / samples_per_ui)
    v = np.full(n, float(symbols[-1]), dtype=float)
    edge = max(1, int(round(rise_ui * samples_per_ui)))
    starts = [0] + [
        max(0, min(n, i * samples_per_ui + int(round((jitter_ui if i % 2 else -jitter_ui) * samples_per_ui))))
        for i in range(1, len(symbols))
    ] + [n]
    prev = float(symbols[0])
    for i, sym in enumerate(symbols):
        start, end = starts[i], starts[i + 1]
        if i == 0:
            v[:end] = sym
        else:
            ramp_end = min(end, start + edge)
            if ramp_end > start:
                v[start:ramp_end] = np.linspace(prev, sym, ramp_end - start, endpoint=False)
            if end > ramp_end:
                v[ramp_end:end] = sym
        prev = float(sym)
    return t, v

def test_clean_nrz_eye_height_and_width():
    bits = [-0.5, 0.5, 0.5, -0.5, 0.5, -0.5, -0.5, 0.5] * 8
    t, v = make_wave(bits, ui_s=100e-12, rise_ui=0.1, jitter_ui=0.0)
    folded = fold_eye(t, v, ui_s=100e-12, samples_per_ui=64, skip_ui=4)
    assert folded["traces"].shape[1] == 128 and folded["traces"].shape[0] > 20
    m = eye_metrics(t, v, ui_s=100e-12, levels=2, skip_ui=4)
    assert abs(m["eye_height_v"] - 1.0) < 0.05
    assert 0.85 < m["eye_width_ui"] <= 1.0
    assert m["jitter_pp_s"] < 5e-12

def test_injected_crossing_jitter_reduces_eye_width():
    bits = [-0.5, 0.5] * 32
    t, v = make_wave(bits, ui_s=100e-12, rise_ui=0.05, jitter_ui=0.1)
    m = eye_metrics(t, v, ui_s=100e-12, levels=2, skip_ui=4)
    assert 15e-12 < m["jitter_pp_s"] < 25e-12
    assert 0.70 < m["eye_width_ui"] < 0.85

def test_pam4_reports_three_open_eyes():
    seq = [-0.75, -0.25, 0.25, 0.75, 0.25, -0.75, 0.75, -0.25] * 10
    t, v = make_wave(seq, ui_s=100e-12, rise_ui=0.08, jitter_ui=0.0)
    m = eye_metrics(t, v, ui_s=100e-12, levels=4, skip_ui=4)
    assert len(m["eye_heights_v"]) == 3
    assert all(abs(h - 0.5) < 0.05 for h in m["eye_heights_v"])
    assert abs(m["eye_height_v"] - 0.5) < 0.05

def test_rejects_invalid_levels():
    with pytest.raises(ValueError, match="levels"):
        eye_metrics([0.0, 1e-10], [0.0, 1.0], ui_s=1e-10, levels=3)
