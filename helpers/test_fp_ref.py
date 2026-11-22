# Tests fp_ref.py's widening against values fixed by the formats themselves (OCP FP4 E2M1: 0, 0.5, 1, 1.5, 2, 3, 4, 6; OCP FP8: E4M3 largest 448 and smallest subnormal 2^-9, NaN only at S.1111.111; E5M2 largest 57344, smallest subnormal 2^-16, infinities; BF16 is the top half of FP32) and its SoftFloat calls on a few exact sums, including MX-scaled products beyond the FP32 range.
import math, struct
import pytest
from fp_ref import widen, f32_value, mul_add, scaled_mul_add, BF16, E4M3, E5M2, E2M1

def test_fp8_limits_and_specials():
    assert f32_value(widen(E4M3, 0x7E)) == 448 and f32_value(widen(E4M3, 0x01)) == 2 ** -9
    assert math.isnan(f32_value(widen(E4M3, 0x7F))) and f32_value(widen(E4M3, 0x78)) == 256
    assert f32_value(widen(E5M2, 0x7B)) == 57344 and f32_value(widen(E5M2, 0x01)) == 2 ** -16
    assert f32_value(widen(E5M2, 0xFC)) == -math.inf and math.isnan(f32_value(widen(E5M2, 0x7D)))
    assert widen(BF16, 0xC0A0) == 0xC0A00000

def test_every_fp8_code_widens_to_its_own_value():
    for code in range(256):
        s, e, m = code >> 7, (code >> 3) & 15, code & 7
        if (e, m) != (15, 7):
            want = (m / 8 if e == 0 else 1 + m / 8) * 2.0 ** ((1 if e == 0 else e) - 7)
            assert f32_value(widen(E4M3, code)) == (-want if s else want)

def test_mul_add_rounds_once():
    one, tiny = 0x3F800000, 0x33800000
    assert mul_add(0x3FC00000, 0x40000000, 0x3E800000) == struct.unpack("<I", struct.pack("<f", 3.25))[0]
    assert mul_add(one, one, tiny) == one
    assert mul_add(0x7F800000, 0, one) == 0x7FC00000

def test_e2m1_values():
    assert [f32_value(widen(E2M1, c)) for c in range(8)] == [0, 0.5, 1, 1.5, 2, 3, 4, 6]
    assert f32_value(widen(E2M1, 0xF)) == -6

def test_scaled_mul_add_rounds_once_even_beyond_fp32():
    one = 0x3F800000
    assert scaled_mul_add(E4M3, 0x38, 0x38, 127, 127, one) == mul_add(one, one, one)
    assert scaled_mul_add(E4M3, 0x38, 0x38, 128, 127, 0) == 0x40000000
    assert scaled_mul_add(E4M3, 0x7E, 0x7E, 254, 200, 0) == 0x7F800000
    assert scaled_mul_add(E4M3, 0x7E, 0x7E, 254, 0, 0xFF7FFFFF) == mul_add(0x43E00000, 0x43E00000, 0xFF7FFFFF)
    assert scaled_mul_add(E4M3, 0x38, 0x38, 0, 106, 0) == 0x00000002
    assert scaled_mul_add(E2M1, 0x2, 0x2, 255, 127, one) == 0x7FC00000
    assert scaled_mul_add(E4M3, 0x38, 0x38, 0, 107, one) == one
