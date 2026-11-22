# Analytical phase-domain loop design, closed-loop phase noise and RMS jitter calculation, and bit-exact integer MASH-111 RTL reference model for projects/frac_n_pll: python3 pll_loop.py.
import math
import numpy as np

def design_loop_filter(f_bw_hz, pm_deg, i_cp_a, k_vco_hz_per_v, n_div):
    if f_bw_hz <= 0 or not (10.0 < pm_deg < 85.0) or i_cp_a <= 0 or k_vco_hz_per_v <= 0 or n_div <= 0:
        raise ValueError("invalid PLL loop design parameters")
    phi = math.radians(pm_deg)
    sqrt_b = (1.0 / math.cos(phi)) + math.tan(phi)
    b = sqrt_b * sqrt_b
    wc = 2.0 * math.pi * f_bw_hz
    c_tot = (i_cp_a * k_vco_hz_per_v * sqrt_b) / (n_div * wc * wc)
    c2 = c_tot / b
    c1 = c_tot - c2
    r1 = sqrt_b / (wc * c1)
    return float(r1), float(c1), float(c2)

def _open_loop(freqs_hz, r1, c1, c2, i_cp_a, k_vco_hz_per_v, n_div):
    s = 1j * 2.0 * np.pi * freqs_hz
    z_lf = (1.0 + s * r1 * c1) / (s * (c1 + c2) * (1.0 + s * r1 * c1 * c2 / (c1 + c2)))
    return (i_cp_a * k_vco_hz_per_v / n_div) * (z_lf / s)

def loop_metrics(r1, c1, c2, i_cp_a, k_vco_hz_per_v, n_div):
    freqs = np.geomspace(1e2, 1e9, 8000)
    g = _open_loop(freqs, r1, c1, c2, i_cp_a, k_vco_hz_per_v, n_div)
    mag = np.abs(g)
    idx = int(np.argmin(np.abs(mag - 1.0)))
    f_bw = float(freqs[idx])
    pm = float(180.0 + np.degrees(np.angle(g[idx])))
    wn = math.sqrt((i_cp_a * k_vco_hz_per_v) / (n_div * (c1 + c2)))
    zeta = 0.5 * r1 * c1 * wn
    lock_time_s = 4.6 / max(1e-9, zeta * wn)
    return {"f_bw_hz": f_bw, "pm_deg": pm, "zeta": float(zeta), "lock_time_s": float(lock_time_s)}

def closed_loop_jitter_s(
    r1, c1, c2, i_cp_a, k_vco_hz_per_v, n_div, f_ref_hz,
    vco_l_1m_dbc, cp_floor_dbc, ref_floor_dbc, f_min_hz=1e4, f_max_hz=1e8,
):
    freqs = np.geomspace(f_min_hz, f_max_hz, 4000)
    g = _open_loop(freqs, r1, c1, c2, i_cp_a, k_vco_hz_per_v, n_div)
    h_lp = g / (1.0 + g)
    h_hp = 1.0 / (1.0 + g)
    l_vco = (10.0 ** (vco_l_1m_dbc / 10.0)) * ((1e6 / freqs) ** 2)
    l_ref = (10.0 ** (ref_floor_dbc / 10.0)) * (n_div ** 2)
    l_cp = 10.0 ** (cp_floor_dbc / 10.0)
    sin_term = 2.0 * np.sin(np.pi * freqs / f_ref_hz)
    l_sdm = 0.5 * (((2.0 * np.pi) ** 2) / (12.0 * f_ref_hz)) * (np.abs(sin_term) ** 4)
    l_tot = (np.abs(h_lp) ** 2) * (l_cp + l_ref + l_sdm) + (np.abs(h_hp) ** 2) * l_vco
    area = float(np.trapezoid(l_tot, freqs))
    f_out = n_div * f_ref_hz
    rms_j = math.sqrt(2.0 * max(0.0, area)) / (2.0 * math.pi * f_out)
    return {"rms_jitter_s": rms_j, "f_out_hz": f_out, "l_out_dbc_hz": 10.0 * np.log10(np.maximum(l_tot, 1e-30))}

def mash111_sequence(frac_in, n_steps, width=20, order=3):
    if order not in (1, 3):
        raise ValueError("order must be 1 or 3")
    mask = (1 << width) - 1
    acc1, acc2, acc3 = 1, 0, 0
    c2_d1, c3_d1, c3_d2 = 0, 0, 0
    out = np.empty(n_steps, dtype=np.int32)
    for idx in range(n_steps):
        sum1 = acc1 + (frac_in & mask)
        c1 = sum1 >> width
        acc1 = sum1 & mask
        sum2 = acc2 + acc1
        c2 = sum2 >> width
        acc2 = sum2 & mask
        sum3 = acc3 + acc2
        c3 = sum3 >> width
        acc3 = sum3 & mask
        if order == 1:
            out[idx] = c1
        else:
            out[idx] = c1 + (c2 - c2_d1) + (c3 - 2 * c3_d1 + c3_d2)
        c2_d1, c3_d1, c3_d2 = c2, c3, c3_d1
    return out

if __name__ == "__main__":
    r1, c1, c2 = design_loop_filter(1.0e6, 60.0, 200e-6, 400e6, 200.0)
    m = loop_metrics(r1, c1, c2, 200e-6, 400e6, 200.0)
    j = closed_loop_jitter_s(r1, c1, c2, 200e-6, 400e6, 200.0, 50e6, -110.0, -105.0, -145.0)
    print(f"R1={r1:.1f} C1={c1*1e12:.2f}pF C2={c2*1e12:.2f}pF bw={m['f_bw_hz']/1e6:.3f}MHz pm={m['pm_deg']:.2f}deg lock={m['lock_time_s']*1e6:.2f}us jitter={j['rms_jitter_s']*1e12:.3f}ps")
