# Computes IEEE Std 1241 sine-wave code-density DNL/INL (arcsine pdf correction, dropping both end codes) plus Walden and Schreier ADC figures of merit: python3 adc_histogram.py codes.txt bits.
import math, sys

def code_density(codes, bits):
    if bits < 2:
        raise ValueError(f"bits must be at least 2, got {bits}")
    levels = 1 << bits
    counts = [0] * levels
    n = 0
    for c in codes:
        ic = int(c)
        if not 0 <= ic < levels:
            raise ValueError(f"code {ic} out of range [0, {levels - 1}]")
        counts[ic] += 1
        n += 1
    if n == 0 or counts[0] == 0 or counts[-1] == 0:
        raise ValueError("sine histogram must overrange both end codes")
    transitions = []
    cum = 0
    for k in range(levels - 1):
        cum += counts[k]
        transitions.append(-math.cos(math.pi * cum / n))
    interior = levels - 2
    avg = (transitions[-1] - transitions[0]) / interior
    dnl = [(transitions[k + 1] - transitions[k]) / avg - 1.0 for k in range(interior)]
    inl, acc = [], 0.0
    for d in dnl:
        acc += d
        inl.append(acc)
    missing = [k for k in range(1, levels - 1) if counts[k] == 0]
    return {
        "codes": list(range(1, levels - 1)),
        "dnl_lsb": dnl,
        "inl_lsb": inl,
        "missing_codes": missing,
        "max_dnl_lsb": max(abs(v) for v in dnl),
        "max_inl_lsb": max(abs(v) for v in inl),
    }

def walden(power_w, enob, fs):
    if power_w <= 0 or fs <= 0:
        raise ValueError("power_w and fs must be positive")
    return power_w / (2.0 ** enob * fs)

def schreier(sndr_db, bw_hz, power_w):
    if bw_hz <= 0 or power_w <= 0:
        raise ValueError("bw_hz and power_w must be positive")
    return sndr_db + 10.0 * math.log10(bw_hz / power_w)

if __name__ == "__main__":
    path, bits = sys.argv[1], int(sys.argv[2])
    codes = [int(v) for v in open(path).read().split()]
    r = code_density(codes, bits)
    print(f"max_dnl_lsb {r['max_dnl_lsb']:.4f}")
    print(f"max_inl_lsb {r['max_inl_lsb']:.4f}")
    print(f"missing_codes {len(r['missing_codes'])}")
