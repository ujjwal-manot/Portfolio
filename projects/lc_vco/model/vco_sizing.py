# Analytical tank sizing, 16-band overlapping tuning coverage, start-up loop gain, power, and Leeson 1 MHz phase noise check for projects/lc_vco: python3 vco_sizing.py.
import math

K_B = 1.380649e-23

def size_vco_tank(f_min_hz=8.8e9, f_max_hz=11.2e9, l_tank_h=0.8e-9, n_bits=4, overlap_ratio=1.6):
    if f_min_hz <= 0 or f_max_hz <= f_min_hz or l_tank_h <= 0:
        raise ValueError("invalid VCO frequency range or inductance")
    c_min = 1.0 / (((2.0 * math.pi * f_max_hz) ** 2) * l_tank_h)
    c_max = 1.0 / (((2.0 * math.pi * f_min_hz) ** 2) * l_tank_h)
    n_steps = (1 << n_bits) - 1
    dc_total = c_max - c_min
    dc_var = (dc_total / (n_steps + overlap_ratio)) * overlap_ratio
    dc_unit = (dc_total - dc_var) / n_steps
    return {
        "l_tank_h": l_tank_h,
        "n_bits": n_bits,
        "c_fixed_f": c_min,
        "dc_var_f": dc_var,
        "dc_unit_f": dc_unit,
        "f_center_hz": 0.5 * (f_min_hz + f_max_hz),
    }

def band_coverage(cfg):
    l_h = cfg["l_tank_h"]
    bands = []
    for code in range(1 << cfg["n_bits"]):
        c_lo = cfg["c_fixed_f"] + code * cfg["dc_unit_f"]
        c_hi = c_lo + cfg["dc_var_f"]
        f_hi = 1.0 / (2.0 * math.pi * math.sqrt(l_h * c_lo))
        f_lo = 1.0 / (2.0 * math.pi * math.sqrt(l_h * c_hi))
        bands.append((f_lo, f_hi))
    overlaps = [bands[k + 1][1] - bands[k][0] for k in range(len(bands) - 1)]
    return {
        "bands_hz": bands,
        "f_lowest_hz": min(b[0] for b in bands),
        "f_highest_hz": max(b[1] for b in bands),
        "min_overlap_hz": min(overlaps),
    }

def vco_specs(cfg, q_tank=14.0, i_tail_a=5.0e-3, vdd_v=1.2, gm_eff_s=12.0e-3, noise_factor=2.5, temp_k=300.0):
    f0 = cfg["f_center_hz"]
    r_p = q_tank * 2.0 * math.pi * f0 * cfg["l_tank_h"]
    startup_gain = 0.5 * gm_eff_s * r_p
    v_amp = min(0.85 * vdd_v, (2.0 / math.pi) * i_tail_a * r_p)
    p_sig = (v_amp * v_amp) / (2.0 * r_p)
    df = 1.0e6
    l_lin = (2.0 * noise_factor * K_B * temp_k / p_sig) * (1.0 + (f0 / (2.0 * q_tank * df)) ** 2)
    return {
        "r_p_ohm": r_p,
        "startup_gain": startup_gain,
        "v_amp_v": v_amp,
        "power_w": vdd_v * i_tail_a,
        "leeson_1m_dbc_hz": 10.0 * math.log10(l_lin),
    }

if __name__ == "__main__":
    cfg = size_vco_tank()
    cov = band_coverage(cfg)
    sp = vco_specs(cfg)
    print(f"bands={cov['f_lowest_hz']/1e9:.2f}-{cov['f_highest_hz']/1e9:.2f}GHz overlap={cov['min_overlap_hz']/1e6:.1f}MHz gmRp/2={sp['startup_gain']:.2f} P={sp['power_w']*1e3:.2f}mW L(1M)={sp['leeson_1m_dbc_hz']:.2f}dBc/Hz")
