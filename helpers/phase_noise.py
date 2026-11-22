# Computes oscillator jitter, single-sideband phase noise L(f) from transient-noise zero crossings, integrated rms jitter, and Leeson's formula cross-check: python3 phase_noise.py wave.txt [threshold].
import math, sys
import numpy as np

KB = 1.380649e-23

def zero_crossings(time_s, voltage_v, threshold=0.0):
    t = np.asarray(time_s, dtype=float)
    v = np.asarray(voltage_v, dtype=float)
    if len(t) < 2 or len(t) != len(v):
        raise ValueError("time_s and voltage_v must have equal length >= 2")
    idx = np.where((v[:-1] < threshold) & (v[1:] >= threshold))[0]
    frac = (threshold - v[idx]) / (v[idx + 1] - v[idx])
    return t[idx] + frac * (t[idx + 1] - t[idx])

def jitter_metrics(crossings_s):
    c = np.asarray(crossings_s, dtype=float)
    if len(c) < 3:
        raise ValueError("need at least 3 crossings")
    periods = np.diff(c)
    t0 = float(periods.mean())
    return {
        "t0_s": t0,
        "f0_hz": 1.0 / t0,
        "period_jitter_s": float(periods.std(ddof=1)),
        "cycle_to_cycle_jitter_s": float(np.diff(periods).std(ddof=1)),
    }

def phase_noise_dbc_hz(crossings_s):
    c = np.asarray(crossings_s, dtype=float)
    n = len(c)
    if n < 8:
        raise ValueError("need at least 8 crossings for phase noise FFT")
    k = np.arange(n, dtype=float)
    t0, intercept = np.polyfit(k, c, 1)
    f0 = 1.0 / float(t0)
    phi = 2.0 * math.pi * (c - (intercept + k * t0)) / t0
    win = np.hanning(n)
    spec = np.fft.rfft(phi * win)
    freqs = np.fft.rfftfreq(n, d=t0)
    s_phi = (2.0 / (f0 * float(np.sum(win ** 2)))) * (np.abs(spec) ** 2)
    mask = freqs > 0.0
    l_lin = np.maximum(0.5 * s_phi[mask], 1e-30)
    return {
        "f0_hz": f0,
        "f_offset_hz": freqs[mask],
        "l_dbc_hz": 10.0 * np.log10(l_lin),
    }

def integrated_jitter_s(f_offset_hz, l_dbc_hz, f0_hz, f_min_hz, f_max_hz):
    f = np.asarray(f_offset_hz, dtype=float)
    l_db = np.asarray(l_dbc_hz, dtype=float)
    sel = (f >= f_min_hz) & (f <= f_max_hz)
    if np.count_nonzero(sel) < 2:
        raise ValueError("fewer than 2 frequency bins in integration band")
    fx = f[sel]
    ly = 2.0 * (10.0 ** (l_db[sel] / 10.0))
    area = float(np.sum(0.5 * (ly[:-1] + ly[1:]) * np.diff(fx)))
    return math.sqrt(max(0.0, area)) / (2.0 * math.pi * f0_hz)

def leeson_dbc_hz(f_offset_hz, f0_hz, q_loaded, power_sig_w, noise_factor=2.0, temp_k=300.0, f_corner_hz=0.0):
    if f_offset_hz <= 0 or f0_hz <= 0 or q_loaded <= 0 or power_sig_w <= 0 or noise_factor <= 0 or temp_k <= 0 or f_corner_hz < 0:
        raise ValueError("Leeson parameters must be positive (f_corner_hz >= 0)")
    val = (2.0 * noise_factor * KB * temp_k / power_sig_w) * (1.0 + (f0_hz / (2.0 * q_loaded * f_offset_hz)) ** 2) * (1.0 + f_corner_hz / f_offset_hz)
    return 10.0 * math.log10(val)

if __name__ == "__main__":
    path = sys.argv[1]
    th = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    arr = np.loadtxt(path)
    zc = zero_crossings(arr[:, 0], arr[:, 1], threshold=th)
    jm = jitter_metrics(zc)
    print(f"f0_hz {jm['f0_hz']:.6g}")
    print(f"period_jitter_s {jm['period_jitter_s']:.6g}")
    print(f"cycle_to_cycle_jitter_s {jm['cycle_to_cycle_jitter_s']:.6g}")
