# Checks the ADC result reader on made-up files: comparator decisions must have the right sign beyond the hysteresis and finish inside the budget, Monte Carlo offsets give their spread, DAC level errors give DNL and INL against chip.md's limits, and converted codes give ENOB from a coherent FFT and an offset and gain error held to chip.md's +-1 and +-2 LSB.
import math, pytest
from adc_results import decisions, offsets, linearity, codes_from_run, check_conversion

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

def conversion(tmp_path, codes, fin):
    rows = []
    for t, code in enumerate([0, 0] + codes):
        for valid in (0, 1):
            bits = [1.2 if code >> (7 - j) & 1 else 0 for j in range(8)]
            rows.append(" ".join(f"{2 * t + valid} {v}" for v in [valid * 1.2] + bits))
    write(tmp_path, "m.txt", f"p_vdd_w 1e-6 p_hi_w 1e-6 p_lo_w -1e-7 p_cm_w 0 fin_hz {fin}\n")
    return write(tmp_path, "c.txt", "\n".join(rows) + "\n"), tmp_path / "m.txt"

def test_a_conversion_needs_the_full_record_and_a_coherent_tone(tmp_path):
    n, k = 128, 5
    codes = [min(255, max(0, math.floor(127.5 + 0.6 + 120.8 * math.sin(2 * math.pi * k * i / n) + 0.5))) for i in range(n)]
    r = check_conversion(*conversion(tmp_path, codes, k * 1e6 / n), 1.2, n)
    assert r["problems"] == [] and abs(r["offset_lsb"] - 0.6) < 0.3 and r["enob"] > 7.5
    assert check_conversion(*conversion(tmp_path, codes[:-1], k * 1e6 / n), 1.2, n)["problems"]
    assert any("not coherent" in p for p in check_conversion(*conversion(tmp_path, codes, (k + 0.3) * 1e6 / n), 1.2, n)["problems"])

def test_offset_and_gain_error_are_held_to_chip_md(tmp_path):
    n, k = 128, 5
    tone = lambda offset, amplitude: [min(255, max(0, math.floor(127.5 + offset + amplitude * math.sin(2 * math.pi * k * i / n) + 0.5))) for i in range(n)]
    shifted = check_conversion(*conversion(tmp_path, tone(3, 120.8), k * 1e6 / n), 1.2, n)
    assert any("offset" in p for p in shifted["problems"])
    stretched = check_conversion(*conversion(tmp_path, tone(0, 124), k * 1e6 / n), 1.2, n)
    assert any("gain error" in p for p in stretched["problems"]) and abs(stretched["gain_error_lsb"] - (124 / 120.83 - 1) * 256) < 0.5
