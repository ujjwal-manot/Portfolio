# Parses Nucleo-H753 UART logs from hardware/stm32_dac/main.c into static 8-bit R-2R DNL/INL metrics and coherent 8-bit codes.txt records for helpers/adc_spectrum.py: python3 capture.py log.txt [codes.txt].
import sys
from pathlib import Path
import numpy as np

def parse_lines(lines):
    ramp, sine = {}, []
    for raw in lines:
        parts = raw.strip().split()
        if not parts:
            continue
        if parts[0] == "R" and len(parts) == 3:
            ramp[int(parts[1])] = int(parts[2])
        elif parts[0] == "S" and len(parts) == 4:
            sine.append((int(parts[1]), int(parts[2]), int(parts[3])))
    return {"ramp": ramp, "sine": sine}

def static_linearity(ramp, n_codes=256):
    if len(ramp) != n_codes or any(c not in ramp for c in range(n_codes)):
        raise ValueError(f"ramp must contain all {n_codes} codes 0..{n_codes - 1}")
    vals = np.array([float(ramp[c]) for c in range(n_codes)], dtype=float)
    span = vals[-1] - vals[0]
    if span <= 0.0:
        raise ValueError("ramp endpoint span must be positive")
    lsb = span / (n_codes - 1)
    dnl = np.zeros(n_codes, dtype=float)
    dnl[1:] = np.diff(vals) / lsb - 1.0
    ideal = vals[0] + np.arange(n_codes, dtype=float) * lsb
    inl = (vals - ideal) / lsb
    return {
        "lsb_adc_counts": float(lsb),
        "dnl_lsb": dnl.tolist(),
        "inl_lsb": inl.tolist(),
        "max_abs_dnl_lsb": float(np.max(np.abs(dnl))),
        "max_abs_inl_lsb": float(np.max(np.abs(inl))),
    }

def sine_to_codes(records, adc_bits=16, dac_bits=8):
    if not records:
        raise ValueError("no sine records to convert")
    ordered = sorted(records, key=lambda r: r[0])
    adc_fs = float((1 << adc_bits) - 1)
    dac_fs = (1 << dac_bits) - 1
    return [max(0, min(dac_fs, int(round(adc_raw * dac_fs / adc_fs)))) for _, _, adc_raw in ordered]

def write_codes(path, codes):
    Path(path).write_text("\n".join(str(int(c)) for c in codes) + "\n", encoding="utf-8")

if __name__ == "__main__":
    log_path = Path(sys.argv[1])
    parsed = parse_lines(log_path.read_text(encoding="utf-8").splitlines())
    if len(parsed["ramp"]) == 256:
        lin = static_linearity(parsed["ramp"])
        print(f"max_abs_dnl_lsb {lin['max_abs_dnl_lsb']:.4f}")
        print(f"max_abs_inl_lsb {lin['max_abs_inl_lsb']:.4f}")
    if parsed["sine"]:
        out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else log_path.with_name("codes.txt")
        codes = sine_to_codes(parsed["sine"])
        write_codes(out_path, codes)
        print(f"wrote {len(codes)} codes to {out_path}")
