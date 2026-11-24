# Checks opamp_model: model constants follow from one corner's measured loop, step and swing numbers (the two-pole loop crosses 0 dB at fc_hz with phase margin pm_deg), step edges are found in the input waveform, a run that ended before the stimulus did fails, and a model waveform passes only within half an LSB of the transistor 200 ns after each edge and with a settling time within 20% (at least 10 ns) of the transistor's.
import cmath, math
import numpy as np
from opamp_model import constants, define, edges, edge_errors, judge, check, ERR_V, END

RESULT = {"fc_hz": 1.6e7, "pm_deg": 65.0, "rise_slew_v_per_s": 2.5e7, "fall_slew_v_per_s": 2.2e7,
          "offset_v": 0.002, "gain_error": 0.01, "out_low_v": 0.02, "out_high_v": 1.12}

def test_constants_reproduce_the_measured_loop():
    c = constants(RESULT)
    assert abs(c["mid"] - 0.604) < 1e-12 and abs(c["slope"] - 1.01) < 1e-12
    assert c["slew_up"] == 2.5e7 and c["slew_down"] == 2.2e7 and c["out_low"] == 0.02 and c["out_high"] == 1.12
    w = 2 * math.pi * 1.6e7
    t = c["wu"] * c["p2"] / (1j * w * (1j * w + c["p2"]))
    assert abs(abs(t) - 1) < 1e-9 and abs(180 + math.degrees(cmath.phase(t)) - 65.0) < 1e-9
    assert define(c).startswith("`define OPAMP_MODEL .mid(")

def test_edges_are_found_where_the_input_moves():
    t = np.linspace(0, 1.2e-6, 12001)
    vin = np.where(t < 50e-9, 1.0, np.where(t < 450e-9, 0.2, np.where(t < 850e-9, 1.0, 0.95)))
    found = edges(t, vin)
    assert len(found) == 3 and all(abs(a - b) < 0.2e-9 for a, b in zip(found, (50e-9, 450e-9, 850e-9)))

def wave(t, te, tau, step, start):
    return start + np.where(t < te, 0, step * (1 - np.exp(-(t - te) / tau)))

def test_identical_waves_pass_and_a_slow_or_offset_model_fails():
    t = np.linspace(0, 450e-9, 45001)
    real = wave(t, 50e-9, 15e-9, 0.8, 0.2)
    err, ts_real, ts_model = edge_errors(t, real, t, real, 50e-9)
    assert err == 0 and ts_real == ts_model and judge(err, ts_real, ts_model)
    slow = wave(t, 50e-9, 15e-9 * 1.3, 0.8, 0.2)
    assert not judge(*edge_errors(t, real, t, slow, 50e-9))
    shifted = real + 2 * ERR_V * (t > 200e-9)
    assert not judge(*edge_errors(t, real, t, shifted, 50e-9))
    near = wave(t, 50e-9, 15e-9 * 1.1, 0.8, 0.2)
    assert judge(*edge_errors(t, real, t, near, 50e-9))

def test_a_transistor_run_that_ended_early_fails(tmp_path):
    t = np.arange(0, END * 0.5, 1e-10)
    vin = np.where(t < 50e-9, 1.0, 0.2)
    vout = 1.2 - vin
    (tmp_path / "wave.txt").write_text("\n".join(f"{a} {b} {a} {c}" for a, b, c in zip(t, vin, vout)))
    (tmp_path / "model.txt").write_text("\n".join(f"{a} {c}" for a, c in zip(t, vout)))
    assert not check([tmp_path.name], [tmp_path])
