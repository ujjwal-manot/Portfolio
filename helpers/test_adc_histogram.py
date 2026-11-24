# Checks IEEE 1241 sine-wave code-density DNL/INL and ADC FoMs (hand-checked against Murmann ADCsurvey_rev20260801.xlsx commit 00b4b855de5c ISSCC 2010 ID 21.6 Harpe et al., row 207: P=6.9e-5 W, fs=10.24e6 Hz, SNDR_hf=48.4 dB, FOMW_hf=31.3557 fJ/conv-step, FOMS_hf=157.1042 dB).
import math, pytest
from adc_histogram import code_density, walden, schreier

def sine_codes(n, k, bits=8, overdrive=1.05):
    levels = 1 << bits
    mid = (levels - 1) / 2.0
    amp = mid * overdrive
    return [min(levels - 1, max(0, math.floor(mid + amp * math.sin(2 * math.pi * k * i / n) + 0.5))) for i in range(n)]

def test_ideal_overranged_sine_has_tiny_dnl_and_inl():
    r = code_density(sine_codes(16384, 509, bits=8, overdrive=1.05), 8)
    assert len(r["dnl_lsb"]) == 254 and len(r["inl_lsb"]) == 254
    assert r["missing_codes"] == []
    assert max(abs(v) for v in r["dnl_lsb"]) < 0.05
    assert max(abs(v) for v in r["inl_lsb"]) < 0.05

def test_double_wide_code_and_missing_code():
    codes = [100 if c == 101 else c for c in sine_codes(16384, 509, bits=8, overdrive=1.05)]
    r = code_density(codes, 8)
    assert r["missing_codes"] == [101]
    assert abs(r["dnl_lsb"][100 - 1] - 1.0) < 0.05
    assert abs(r["dnl_lsb"][101 - 1] - (-1.0)) < 1e-9

def test_requires_overrange_on_both_ends():
    with pytest.raises(ValueError, match="overrange"):
        code_density(sine_codes(4096, 127, bits=8, overdrive=0.9), 8)

def test_walden_and_schreier_match_murmann_survey_row():
    sndr_db, fs, power_w = 48.4, 10.24e6, 6.9e-5
    enob = (sndr_db - 1.76) / 6.02
    assert abs(walden(power_w, enob, fs) - 31.355717e-15) < 1e-18
    assert abs(schreier(sndr_db, fs / 2, power_w) - 157.104209) < 1e-4
