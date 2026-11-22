# Bit-exact digital RTL reference models for projects/serdes_link: PRBS7/PRBS31 generator and checker, 1-tap sign-sign LMS DFE, bang-bang PI CDR tracker, and PAM4 Gray slicer.
import math
import numpy as np

def prbs_generate(order=7, length=256, seed=None):
    if order not in (7, 31):
        raise ValueError("order must be 7 or 31")
    tap = 27 if order == 31 else 5
    mask = (1 << order) - 1
    state = (mask if seed is None else (seed & mask)) or 1
    out = []
    for _ in range(length):
        bit = (state >> (order - 1)) & 1
        out.append(bit)
        fb = ((state >> (order - 1)) ^ (state >> tap)) & 1
        state = ((state << 1) | fb) & mask
    return out

def prbs_check(bits, order=7):
    if order not in (7, 31):
        raise ValueError("order must be 7 or 31")
    tap = 27 if order == 31 else 5
    mask = (1 << order) - 1
    state = 0
    errors = 0
    for idx, b in enumerate(bits):
        b = int(b) & 1
        pred = ((state >> (order - 1)) ^ (state >> tap)) & 1
        if idx >= order and b != pred:
            errors += 1
        state = ((state << 1) | b) & mask
    return errors

def dfe_lms_run(samples, target_amp=64, flip_sign=False):
    h1 = 0
    prev_bit = 0
    decisions = []
    for x in samples:
        eq = int(x) - (h1 if prev_bit else -h1)
        cur_bit = 1 if eq >= 0 else 0
        err = eq - (target_amp if cur_bit else -target_amp)
        err_pos = 1 if err >= 0 else 0
        step = 1 if (err_pos == prev_bit) else -1
        if flip_sign:
            step = -step
        h1 = max(-127, min(127, h1 + step))
        decisions.append(cur_bit)
        prev_bit = cur_bit
    ideal = [1 if int(x) >= 0 else 0 for x in samples]
    tail_len = max(1, len(samples) // 4)
    tail_err = sum(
        1 for i in range(len(samples) - tail_len, len(samples))
        if (decisions[i] == 1) != ((int(samples[i]) - (round(h1) if decisions[i - 1] else -round(h1))) >= 0)
    )
    return {"h1_final": h1, "decisions": decisions, "tail_errors": tail_err, "raw_decisions": ideal}

def bb_cdr_track(n_ui=4000, ppm_offset=200.0, pi_bits=6, kp=1.0, ki=0.05):
    step_ui = 1.0 / (1 << pi_bits)
    tx_phase = 0.0
    rx_phase = 0.25
    freq_int = 0.0
    wraps = 0
    prev_code = int(math.floor(rx_phase / step_ui)) % (1 << pi_bits)
    errs = []
    for idx in range(n_ui):
        tx_phase += ppm_offset * 1e-6
        err = tx_phase - rx_phase
        vote = 1.0 if err > 0.0 else (-1.0 if err < 0.0 else 0.0)
        freq_int += ki * vote
        rx_phase += (kp * vote + freq_int) * step_ui
        code = int(math.floor(rx_phase / step_ui)) % (1 << pi_bits)
        if abs(code - prev_code) > (1 << (pi_bits - 1)):
            wraps += 1
        prev_code = code
        if idx >= n_ui // 2:
            errs.append(abs(tx_phase - rx_phase))
    return {"max_tail_phase_err_ui": max(errs) if errs else 0.0, "wraps": wraps, "final_err_ui": tx_phase - rx_phase}

def pam4_slice(samples, thresholds=(-0.5, 0.0, 0.5)):
    t0, t1, t2 = thresholds
    out = []
    for v in np.asarray(samples, dtype=float):
        if v < t0:
            out.append((0, 0))
        elif v < t1:
            out.append((0, 1))
        elif v < t2:
            out.append((1, 1))
        else:
            out.append((1, 0))
    return out
