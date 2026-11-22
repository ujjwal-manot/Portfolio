# End-to-end whole_chip signal quantization chain, bit-exact 8-tap symmetric FIR reference matching firmware/fir8_dvfs.hex, and DVFS energy-per-frame table from projects/power_manager/results/speed.log.
import re
from pathlib import Path

FIR8_TAPS = (1, 2, 3, 4, 4, 3, 2, 1)

def analog_chain_quantize(vin_samples_v, opamp_vos_v=0.0, adc_vos_lsb=0.0, vref_lo=0.2, vref_hi=1.0, vcm=0.6):
    lsb = (vref_hi - vref_lo) / 256.0
    codes = []
    for vin in vin_samples_v:
        v_amp = (2.0 * vcm - float(vin)) + 2.0 * opamp_vos_v
        raw = int(round((v_amp - vref_lo) / lsb + adc_vos_lsb))
        codes.append(max(0, min(255, raw)))
    return codes

def fir8_reference(raw_codes, init_hist=None):
    hist = [0] * 7 if init_hist is None else [int(v) for v in init_hist[-7:]]
    if len(hist) < 7:
        hist = [0] * (7 - len(hist)) + hist
    out = []
    for raw in raw_codes:
        x0 = int(raw) ^ 0xFF
        window = [x0] + list(reversed(hist))
        y = sum(t * v for t, v in zip(FIR8_TAPS, window))
        out.append(y)
        hist = hist[1:] + [x0]
    return out

def dvfs_energy_table(speed_log_path, cpu_power_1v2_w=9.0e-3, frame_cycles=1850, base_freq_hz=50e6):
    text = Path(speed_log_path).read_text(encoding="utf-8")
    factors = {}
    for m in re.finditer(r"vdd\s+([0-9.]+)\s+V:\s+worst\s+slow-corner\s+delay\s+([0-9.]+)\s+x", text):
        factors[round(float(m.group(1)), 2)] = float(m.group(2))
    rows = []
    e_ref_j = cpu_power_1v2_w * (frame_cycles / base_freq_hz)
    for vdd in (0.90, 1.00, 1.10, 1.20):
        fac = factors[vdd]
        f_max_hz = min(base_freq_hz, base_freq_hz / fac)
        scale_v2 = (vdd / 1.20) ** 2
        e_frame_j = e_ref_j * scale_v2
        p_active_w = cpu_power_1v2_w * scale_v2 * (f_max_hz / base_freq_hz)
        rows.append({
            "vdd_v": vdd,
            "delay_factor": fac,
            "f_max_mhz": f_max_hz / 1e6,
            "active_power_mw": p_active_w * 1e3,
            "energy_per_frame_nj": e_frame_j * 1e9,
        })
    return rows
