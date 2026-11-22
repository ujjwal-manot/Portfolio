# Folds transient simulator waveforms into NRZ or PAM4 eye diagrams and computes eye height, eye width, and crossing jitter: python3 eye_diagram.py wave.txt ui_s [levels].
import sys
import numpy as np

def fold_eye(time_s, voltage_v, ui_s, samples_per_ui=64, skip_ui=0):
    t = np.asarray(time_s, dtype=float)
    v = np.asarray(voltage_v, dtype=float)
    if ui_s <= 0 or samples_per_ui < 8:
        raise ValueError("ui_s must be positive and samples_per_ui >= 8")
    if len(t) < 2 or len(t) != len(v):
        raise ValueError("time_s and voltage_v must have equal length >= 2")
    t_start = t[0] + skip_ui * ui_s
    span = 2.0 * ui_s
    grid = np.linspace(0.0, span, 2 * samples_per_ui, endpoint=False)
    n_seg = int((t[-1] - t_start - span) / ui_s) + 1
    if n_seg < 1:
        raise ValueError("waveform is shorter than skip_ui + 2 UI")
    starts = t_start + np.arange(n_seg, dtype=float) * ui_s
    traces = np.vstack([np.interp(s + grid, t, v) for s in starts])
    return {"t_ui": grid / ui_s, "traces": traces}

def _vertical_openings(values, v_min, v_max, levels):
    if levels == 2:
        th = [0.5 * (v_min + v_max)]
    else:
        step = (v_max - v_min) / 3.0
        th = [v_min + 0.5 * step, v_min + 1.5 * step, v_min + 2.5 * step]
    bounds = [-np.inf, *th, np.inf]
    bands = [values[(values >= bounds[i]) & (values < bounds[i + 1])] for i in range(levels)]
    heights = []
    for k in range(levels - 1):
        if len(bands[k]) == 0 or len(bands[k + 1]) == 0:
            heights.append(0.0)
        else:
            heights.append(max(0.0, float(bands[k + 1].min() - bands[k].max())))
    return heights, th

def eye_metrics(time_s, voltage_v, ui_s, levels=2, skip_ui=0, samples_per_ui=64):
    if levels not in (2, 4):
        raise ValueError(f"levels must be 2 (NRZ) or 4 (PAM4), got {levels}")
    folded = fold_eye(time_s, voltage_v, ui_s, samples_per_ui=samples_per_ui, skip_ui=skip_ui)
    traces = folded["traces"]
    v_min, v_max = float(traces.min()), float(traces.max())
    all_heights, all_th = [], []
    for col in range(samples_per_ui):
        heights, th = _vertical_openings(traces[:, col], v_min, v_max, levels)
        all_heights.append(heights)
        all_th.append(th)
    mins = [min(h) for h in all_heights]
    max_min = max(mins)
    if max_min > 0.0:
        open_mask = [m >= 0.99 * max_min for m in mins]
        best_start, best_len, run_start, run_len = 0, 0, 0, 0
        for idx in range(2 * samples_per_ui):
            if open_mask[idx % samples_per_ui]:
                if run_len == 0:
                    run_start = idx
                run_len += 1
                if run_len > best_len:
                    best_start, best_len = run_start, min(run_len, samples_per_ui)
            else:
                run_len = 0
        best_col = (best_start + best_len // 2) % samples_per_ui
    else:
        best_col = 0
    best_heights, thresholds = all_heights[best_col], all_th[best_col]
    mid_th = thresholds[len(thresholds) // 2]
    win = traces[:, best_col : best_col + samples_per_ui + 1]
    crossings = []
    for row in win:
        d = row - mid_th
        for idx in np.where((d[:-1] * d[1:]) <= 0.0)[0]:
            denom = row[idx + 1] - row[idx]
            frac = 0.0 if denom == 0.0 else (mid_th - row[idx]) / denom
            crossings.append((idx + frac) / samples_per_ui)
    if crossings:
        c_arr = np.asarray(crossings, dtype=float)
        jitter_ui = float(c_arr.max() - c_arr.min())
    else:
        jitter_ui = 0.0
    return {
        "eye_height_v": min(best_heights),
        "eye_heights_v": best_heights,
        "eye_width_ui": max(0.0, 1.0 - jitter_ui),
        "jitter_pp_s": jitter_ui * ui_s,
        "sample_phase_ui": best_col / samples_per_ui,
        "thresholds_v": thresholds,
    }

if __name__ == "__main__":
    path, ui = sys.argv[1], float(sys.argv[2])
    lv = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    arr = np.loadtxt(path)
    m = eye_metrics(arr[:, 0], arr[:, 1], ui, levels=lv)
    print(f"eye_height_v {m['eye_height_v']:.6g}")
    print(f"eye_width_ui {m['eye_width_ui']:.4f}")
    print(f"jitter_pp_s {m['jitter_pp_s']:.6g}")
