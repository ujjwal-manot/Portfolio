# Checks the ADC result reader on made-up files: comparator decisions must have the right sign beyond the hysteresis and finish inside the budget, Monte Carlo offsets give their spread, DAC level errors give DNL and INL against chip.md's limits, two DAC level runs agree to a hundredth of an LSB, two conversions give the same codes, and converted codes give ENOB from a coherent FFT and an offset and gain error held to chip.md's +-1 and +-2 LSB.
import math, pytest
from adc_results import decisions, offsets, linearity, codes_from_run, check_conversion, compare_supplied, same, same_codes, top_difference, decide_difference

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

def conversion(tmp_path, codes, fin, powers="p_vdd_w 1e-6 p_hi_w 1e-6 p_lo_w -1e-7 p_cm_w 0"):
    rows = []
    for t, code in enumerate([0, 0] + codes):
        for valid in (0, 1):
            bits = [1.2 if code >> (7 - j) & 1 else 0 for j in range(8)]
            rows.append(" ".join(f"{2 * t + valid} {v}" for v in [valid * 1.2] + bits))
    write(tmp_path, "m.txt", f"{powers} fin_hz {fin}\n")
    return write(tmp_path, "c.txt", "\n".join(rows) + "\n"), tmp_path / "m.txt"

def test_a_conversion_needs_the_full_record_and_a_coherent_tone(tmp_path):
    n, k = 128, 5
    codes = [min(255, max(0, math.floor(127.5 + 0.6 + 120.8 * math.sin(2 * math.pi * k * i / n) + 0.5))) for i in range(n)]
    r = check_conversion(*conversion(tmp_path, codes, k * 1e6 / n), 1.2, n)
    assert r["problems"] == [] and abs(r["offset_lsb"] - 0.6) < 0.3 and r["enob"] > 7.5
    assert check_conversion(*conversion(tmp_path, codes[:-1], k * 1e6 / n), 1.2, n)["problems"]
    assert any("not coherent" in p for p in check_conversion(*conversion(tmp_path, codes, (k + 0.3) * 1e6 / n), 1.2, n)["problems"])

def test_power_adds_every_p_entry_and_ignores_the_rest(tmp_path):
    n, k = 128, 5
    codes = [min(255, max(0, math.floor(127.5 + 120.8 * math.sin(2 * math.pi * k * i / n) + 0.5))) for i in range(n)]
    assert abs(check_conversion(*conversion(tmp_path, codes, k * 1e6 / n), 1.2, n)["power_w"] - 2.1e-6) < 1e-12
    assert abs(check_conversion(*conversion(tmp_path, codes, k * 1e6 / n, "p_sup_w 3e-4 code 9"), 1.2, n)["power_w"] - 3e-4) < 1e-12

def test_a_supplied_conversion_may_lose_at_most_a_quarter_bit(tmp_path):
    n, k = 128, 5
    tone = lambda noise: [min(255, max(0, math.floor(127.5 + 120.8 * math.sin(2 * math.pi * k * i / n) + noise * ((i * 37) % 11 - 5) + 0.5))) for i in range(n)]
    (tmp_path / "a").mkdir(); (tmp_path / "b").mkdir(); (tmp_path / "c").mkdir()
    ideal = conversion(tmp_path / "a", tone(0), k * 1e6 / n)
    close = conversion(tmp_path / "b", tone(0.02), k * 1e6 / n, "p_sup_w 3e-4")
    worse = conversion(tmp_path / "c", tone(0.3), k * 1e6 / n, "p_sup_w 3e-4")
    r = compare_supplied(*close, *ideal, 1.2, n)
    assert r["problems"] == [] and r["enob_loss"] < 0.25
    assert any("quarter" in p for p in compare_supplied(*worse, *ideal, 1.2, n)["problems"])

def test_offset_and_gain_error_are_held_to_chip_md(tmp_path):
    n, k = 128, 5
    tone = lambda offset, amplitude: [min(255, max(0, math.floor(127.5 + offset + amplitude * math.sin(2 * math.pi * k * i / n) + 0.5))) for i in range(n)]
    shifted = check_conversion(*conversion(tmp_path, tone(3, 120.8), k * 1e6 / n), 1.2, n)
    assert any("offset" in p for p in shifted["problems"])
    stretched = check_conversion(*conversion(tmp_path, tone(0, 124), k * 1e6 / n), 1.2, n)
    assert any("gain error" in p for p in stretched["problems"]) and abs(stretched["gain_error_lsb"] - (124 / 120.83 - 1) * 256) < 0.5

def test_two_level_runs_must_agree_to_a_hundredth_of_an_lsb(tmp_path):
    rows = "code error_v\n" + "".join(f"{c} {1e-5 * c}\n" for c in range(256))
    a, b = write(tmp_path, "a.txt", rows), write(tmp_path, "b.txt", rows.replace("100 0.001", "100 0.00102"))
    assert same(a, b)[0] and abs(same(a, b)[1] - 2e-5 / 0.003125) < 1e-9
    assert not same(a, write(tmp_path, "c.txt", rows.replace("100 0.001", "100 0.0011")))[0]

def test_two_conversions_must_give_the_same_codes(tmp_path):
    a = conversion(tmp_path, [10, 200, 7], 1e3)[0].read_text()
    b, c = write(tmp_path, "b.txt", a), write(tmp_path, "c.txt", conversion(tmp_path, [10, 201, 7], 1e3)[0].read_text())
    a = write(tmp_path, "a.txt", a)
    assert same_codes(a, b, 1.2) == (True, 0)
    assert same_codes(a, c, 1.2) == (False, 1)

def run_at_steps(tmp_path, name, steps):
    rows = [" ".join(f"{time} {v}" for v in (cclk, top, 0.6)) for time, cclk, top in steps]
    return write(tmp_path, name, "\n".join(rows) + "\n")

def test_top_plate_is_read_at_each_comparator_clock_rise(tmp_path):
    gear = run_at_steps(tmp_path, "g.txt", [(0, 0, 0.61), (1e-9, 1.2, 0.62), (2e-9, 0, 0.63), (4e-9, 1.2, 0.65)])
    trap = run_at_steps(tmp_path, "t.txt", [(0, 0, 0.61), (2e-9, 1.2, 0.6206), (3e-9, 0, 0.63), (5e-9, 1.2, 0.65)])
    worst, points = top_difference(gear, trap, 1.2)
    assert points == 2 and abs(worst - 0.0003 / 0.003125) < 1e-6

def test_a_missing_decision_counts_as_a_difference(tmp_path):
    gear = run_at_steps(tmp_path, "g.txt", [(0, 0, 0.6), (1e-9, 1.2, 0.6), (2e-9, 0, 0.6), (3e-9, 1.2, 0.6)])
    trap = run_at_steps(tmp_path, "t.txt", [(0, 0, 0.6), (1e-9, 1.2, 0.6), (2e-9, 0, 0.6)])
    assert top_difference(gear, trap, 1.2)[0] == float("inf")

def test_decision_times_are_compared_row_by_row(tmp_path):
    a = write(tmp_path, "a.txt", "dv_v t_decide_s outp_v\n1e-3 3.0e-10 1.2\n-1e-3 3.2e-10 0\n")
    b = write(tmp_path, "b.txt", "dv_v t_decide_s outp_v\n1e-3 3.3e-10 1.2\n-1e-3 3.2e-10 0\n")
    assert abs(decide_difference(a, b) - 0.1) < 1e-9

def test_nan_in_a_result_is_refused(tmp_path):
    import pytest
    from adc_results import linearity
    p = tmp_path / "levels.txt"
    p.write_text("code error_v\n0 0\n1 nan\n2 0\n")
    with pytest.raises(ValueError, match="not a number"):
        linearity(p)

def test_level_readers_skip_the_bench_line_that_says_code_zero_is_real(tmp_path):
    text = "code e_v\nzero is real: code (the first DAC code)\n0 0.001\n1 0.001\n2 0.0011\n"
    a = tmp_path / "a.txt"
    a.write_text(text)
    assert linearity(a)["dnl_max"] < 0.1 and same(a, a)[0]
