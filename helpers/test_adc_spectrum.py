# Checks the ADC spectrum reader on made-up code sequences: an ideal 8-bit quantizer of a coherent near-full-scale sine scores ENOB close to 8, a code sequence with a known third harmonic shows that spur in SFDR, and a tone that does not fit a whole number of cycles in the record is refused.
import math, pytest
from adc_spectrum import spectrum, coherent_bin

def quantized(n, k, amplitude_lsb=127.5 * 10 ** (-0.5 / 20), third=0.0):
    out = []
    for i in range(n):
        x = 127.5 + amplitude_lsb * math.sin(2 * math.pi * k * i / n) + third * math.sin(2 * math.pi * 3 * k * i / n)
        out.append(min(255, max(0, math.floor(x + 0.5))))
    return out

def test_ideal_quantizer_scores_about_eight_bits():
    r = spectrum(quantized(1024, 31), 31)
    assert 7.9 < r["enob"] < 8.1 and r["sfdr_db"] > 55

def test_a_third_harmonic_sets_sfdr():
    r = spectrum(quantized(1024, 31, third=4.0), 31)
    assert abs(r["sfdr_db"] - 20 * math.log10(127.5 * 10 ** (-0.5 / 20) / 4.0)) < 1.5

def test_tone_must_be_coherent():
    assert coherent_bin(1e6, 1024, 30.2734375e3) == 31
    with pytest.raises(ValueError, match="not coherent"):
        coherent_bin(1e6, 1024, 30.3e3)
    with pytest.raises(ValueError, match="not coherent"):
        coherent_bin(1e6, 1024, 31.25e3)
