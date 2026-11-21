# Turns a record of ADC output codes taken from a coherent sine (no window: the tone sits in one FFT bin) into SNDR, SFDR, ENOB and the tone level in dBFS, and refuses a tone that is not coherent with the record (a whole number of cycles, sharing no factor with the record length): python3 adc_spectrum.py codes.txt sample_rate tone_frequency.
import math, sys
import numpy as np

def coherent_bin(fs, n, fin):
    k = fin * n / fs
    if abs(k - round(k)) > 1e-6 or math.gcd(round(k), n) != 1 or not 0 < round(k) < n // 2:
        raise ValueError(f"tone {fin} Hz is not coherent with {n} samples at {fs} Hz (bin {k:.4f})")
    return round(k)

def spectrum(codes, k):
    x = np.asarray(codes, float)
    p = np.abs(np.fft.rfft(x - x.mean())) ** 2
    rest = np.delete(p[1:], k - 1)
    amplitude = 2 * math.sqrt(p[k]) / len(x)
    sndr = 10 * math.log10(p[k] / rest.sum())
    return {"sndr_db": sndr, "enob": (sndr - 1.76) / 6.02, "sfdr_db": 10 * math.log10(p[k] / rest.max()), "tone_dbfs": 20 * math.log10(amplitude / 128)}

if __name__ == "__main__":
    path, fs, fin = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    codes = [int(v) for v in open(path).read().split()]
    for key, value in spectrum(codes, coherent_bin(fs, len(codes), fin)).items():
        print(f"{key} {value:.4f}")
