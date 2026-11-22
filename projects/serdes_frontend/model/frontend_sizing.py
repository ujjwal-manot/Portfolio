# Analytical 10 GBd SerDes front-end sizing model for projects/serdes_frontend: differential CTLE peaking transfer function, 3-tap FFE ISI cancellation, pad+ESD return loss S11, and CML TX swing and energy efficiency.
import math
import numpy as np

def ctle_peaking_db(gm_s, r_d_ohm, c_d_f, r_s_ohm, c_s_f, f_nyq_hz=5e9):
    freqs = np.geomspace(1e6, 50e9, 4000)
    s = 1j * 2.0 * np.pi * freqs
    h = (gm_s * r_d_ohm * (1.0 + s * r_s_ohm * c_s_f)) / (
        (1.0 + 0.5 * gm_s * r_s_ohm + s * r_s_ohm * c_s_f) * (1.0 + s * r_d_ohm * c_d_f)
    )
    mag_db = 20.0 * np.log10(np.abs(h))
    gain_dc_db = float(mag_db[0])
    peak_idx = int(np.argmax(mag_db))
    nyq_idx = int(np.argmin(np.abs(freqs - f_nyq_hz)))
    return {
        "gain_dc_db": gain_dc_db,
        "gain_nyq_db": float(mag_db[nyq_idx]),
        "peak_gain_db": float(mag_db[peak_idx]),
        "peak_freq_hz": float(freqs[peak_idx]),
        "peaking_db": float(mag_db[peak_idx] - gain_dc_db),
    }

def ffe_equalize_pulse(channel_pulse, taps=(-0.08, 1.0, -0.30)):
    p = np.asarray(channel_pulse, dtype=float)
    w = np.asarray(taps, dtype=float)
    w = w / np.sum(np.abs(w))
    eq = np.convolve(p, w)
    main_idx = int(np.argmax(np.abs(eq)))
    main_val = abs(float(eq[main_idx]))
    isi_sum = float(np.sum(np.abs(eq)) - main_val)
    return {"equalized": eq.tolist(), "main_cursor": main_val, "isi_sum": isi_sum, "isi_ratio": isi_sum / max(1e-12, main_val)}

def return_loss_db(f_hz, r_term_ohm=50.0, c_pad_f=120e-15, z0_ohm=50.0):
    y_in = (1.0 / r_term_ohm) + 1j * 2.0 * math.pi * f_hz * c_pad_f
    z_in = 1.0 / y_in
    gamma = (z_in - z0_ohm) / (z_in + z0_ohm)
    return float(20.0 * math.log10(max(1e-12, abs(gamma))))

def cml_tx_metrics(i_tail_a=12e-3, r_load_ohm=50.0, vdd_v=1.2, data_rate_gbps=10.0):
    diff_swing_vpp = i_tail_a * r_load_ohm
    power_w = vdd_v * i_tail_a
    pj_per_bit = (power_w * 1e12) / (data_rate_gbps * 1e9)
    return {"diff_swing_vpp": diff_swing_vpp, "power_w": power_w, "pj_per_bit": pj_per_bit}

if __name__ == "__main__":
    pk = ctle_peaking_db(10e-3, 120.0, 45e-15, 450.0, 320e-15)
    s11 = return_loss_db(5e9)
    tx = cml_tx_metrics()
    print(f"CTLE peak={pk['peaking_db']:.2f}dB@{pk['peak_freq_hz']/1e9:.2f}GHz S11(5G)={s11:.2f}dB TX={tx['diff_swing_vpp']:.2f}Vpp {tx['pj_per_bit']:.2f}pJ/b")
