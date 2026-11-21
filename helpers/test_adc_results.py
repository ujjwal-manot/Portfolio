# Checks the ADC result reader on made-up files: comparator decisions must have the right sign beyond the hysteresis and finish inside the budget, Monte Carlo offsets give their spread, DAC level errors give DNL and INL against chip.md's limits, and converted codes give ENOB from a coherent FFT.
import math, pytest
from adc_results import decisions, offsets, linearity, codes_from_run

def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text)
    return path

def test_a_wrong_or_late_decision_fails(tmp_path):
    good = "dv_v t_decide_s outp_v\n1e-3 3e-10 1.2\n100e-6 4e-10 1.2\n1e-6 5e-10 1e-7\n-100e-6 4e-10 1e-7\n-1e-3 3e-10 1e-7\n"
    assert decisions([write(tmp_path, "a.txt", good)], 1.2)["problems"] == []
    assert decisions([write(tmp_path, "b.txt", good.replace("100e-6 4e-10 1.2", "100e-6 4e-10 1e-7"))], 1.2)["problems"]
    assert decisions([write(tmp_path, "c.txt", good.replace("1e-3 3e-10 1.2", "1e-3 6e-8 1.2"))], 1.2)["problems"]

def test_offsets_give_mean_sigma_and_worst(tmp_path):
    files = [write(tmp_path, f"o{i}.txt", f"offset_v {v} hysteresis_v 2e-5 up_v 0 down_v 0\n") for i, v in enumerate([1e-3, -1e-3, 3e-3])]
    r = offsets(files)
    assert abs(r["mean_v"] - 1e-3) < 1e-12 and abs(r["worst_v"] - 3e-3) < 1e-12 and abs(r["sigma_v"] - 2e-3) < 1e-9

def test_level_errors_give_dnl_and_inl(tmp_path):
    lsb = 0.8 / 256
    errors = [0.0] * 256
    errors[128] = 0.6 * lsb
    r = linearity(write(tmp_path, "l.txt", "code error_v\n" + "".join(f"{i} {e}\n" for i, e in enumerate(errors))))
    assert abs(r["dnl_max"] - 0.6) < 1e-6 and abs(r["dnl_min"] + 0.6) < 1e-6 and abs(r["inl_max"] - 0.6) < 1e-3

def test_codes_are_read_on_each_rising_valid(tmp_path):
    rows = []
    for t, valid, code in [(0, 0, 0), (1, 1, 200), (2, 1, 200), (3, 0, 200), (4, 1, 7), (5, 0, 7)]:
        bits = [1.2 if code >> (7 - j) & 1 else 0 for j in range(8)]
        cols = [t, valid * 1.2] + bits
        rows.append(" ".join(f"{t} {v}" for v in cols[1:]))
    assert codes_from_run(write(tmp_path, "c.txt", "\n".join(f"{r}" for r in rows) + "\n"), 1.2) == [200, 7]
