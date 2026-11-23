# Checks adc_model's table and metrics on made-up transistor results: the table turns DAC level errors and trim shifts into input volts with the measured top-plate gain and holds exactly 386 numbers, a table with a missing level is refused, and an ideal quantizer's codes score about 7.9 bits with no offset or gain error.
import math
import pytest
from adc_model import table, metrics, LO, LSB, N, K, AMP

def levels(tmp_path, n=256):
    p = tmp_path / "levels.txt"
    p.write_text("code error_v\n" + "".join(f"{c} 2e-4\n" for c in range(n)))
    return p

def trim(tmp_path, step=2.9e-3):
    p = tmp_path / "trim.txt"
    p.write_text("code shift_v\n" + "".join(f"{c} {(c - 63) * 4e-4 + 2e-4}\n" for c in range(128)) + "".join(f"pair_{k} 2e-4 {2e-4 + step}\n" for k in range(8)))
    return p

def test_table_in_input_volts(tmp_path):
    level, shift = table(levels(tmp_path), trim(tmp_path), 1e-3, 2e-3, tmp_path / "t.txt")
    g = 2.9e-3 * 257 / 0.8
    assert abs(level[10] - (LO + 10 * LSB + 2e-4 / g)) < 1e-15
    assert shift[63] == 0 and abs(shift[64] - 4e-4 / g) < 1e-15
    assert len((tmp_path / "t.txt").read_text().split()) == 386

def test_missing_level_is_refused(tmp_path):
    with pytest.raises(ValueError):
        table(levels(tmp_path, 255), trim(tmp_path), 0, 0, tmp_path / "t.txt")

def test_ideal_codes(tmp_path):
    codes = [math.floor(127.5 + 0.5 + AMP / LSB * math.sin(2 * math.pi * K * i / N)) for i in range(N)]
    m = metrics(codes)
    assert 7.7 < m["enob"] < 8.1 and abs(m["offset_lsb"]) < 0.1 and abs(m["gain_error_lsb"]) < 0.5
