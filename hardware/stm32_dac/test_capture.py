# Checks hardware/stm32_dac/capture.py: UART log parsing, endpoint-corrected static DNL/INL on an 8-bit R-2R ramp, and coherent sine export into helpers/adc_spectrum.py.
import math, sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "helpers"))
from adc_spectrum import coherent_bin, spectrum
from capture import parse_lines, static_linearity, sine_to_codes, write_codes

def test_parse_lines_separates_ramp_and_sine_records():
    lines = [
        "EDGESENSE_STM32_DAC_READY",
        "R 0 120",
        "R 255 65400",
        "S 0 128 32768",
        "S 1 138 35328",
        "",
    ]
    parsed = parse_lines(lines)
    assert parsed["ramp"] == {0: 120, 255: 65400}
    assert parsed["sine"] == [(0, 128, 32768), (1, 138, 35328)]

def test_static_linearity_ideal_and_perturbed_ramp():
    ideal = {c: int(round(500 + c * (64000.0 / 255.0))) for c in range(256)}
    res = static_linearity(ideal)
    assert res["max_abs_dnl_lsb"] < 0.01
    assert res["max_abs_inl_lsb"] < 0.01
    step = 64000.0 / 255.0
    broken = dict(ideal)
    broken[128] = int(round(ideal[128] + 0.5 * step))
    bad = static_linearity(broken)
    assert abs(bad["dnl_lsb"][128] - 0.5) < 0.02
    assert abs(bad["dnl_lsb"][129] + 0.5) < 0.02
    assert abs(bad["inl_lsb"][128] - 0.5) < 0.02

def test_sine_capture_feeds_adc_spectrum_coherently(tmp_path):
    fs, n, k = 10000.0, 1024, 13
    fin = fs * k / n
    records = []
    for i in range(n):
        dac = int(round(127.5 + 127.0 * math.sin(2.0 * math.pi * k * i / n)))
        adc = int(round(dac * (65535.0 / 255.0)))
        records.append((i, dac, adc))
    codes = sine_to_codes(records)
    assert len(codes) == n and min(codes) >= 0 and max(codes) <= 255
    out = tmp_path / "codes.txt"
    write_codes(out, codes)
    reloaded = [int(v) for v in out.read_text().split()]
    got = spectrum(reloaded, coherent_bin(fs, len(reloaded), fin))
    assert got["enob"] > 7.8 and got["sndr_db"] > 48.5

def test_static_linearity_rejects_incomplete_ramp():
    with pytest.raises(ValueError, match="256"):
        static_linearity({0: 0, 1: 256})
