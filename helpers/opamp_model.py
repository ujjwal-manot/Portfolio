# Fits and checks the opamp's real-number model (design/opamp_model.sv): "define" turns one corner's measured loop crossover and phase margin, 20-80% slew rates, offset, gain error and output range into the model's constants (a two-pole loop with those numbers, a slew limit and an output clamp), and "check" compares model and transistor output waveforms edge by edge, passing only if, at every corner and edge, the model is within half an LSB (0.8 V / 256 / 2) of the transistor 200 ns after the edge (the ADC's sampling time) and its settling time to half an LSB is within 20% (at least 10 ns) of the transistor's; edges before 850 ns at the fit corners are the fit set (the 0.8 V steps of tests/step.cir), every other edge and corner is the validation set; a transistor or model run that ends before the stimulus's 3.65 us fails. Run as: opamp_model.py define result.txt, or opamp_model.py check "fit corners" folder...
import math, sys
from pathlib import Path
import numpy as np
from analog_results import parse

ERR_V, WINDOW, FINAL, SETTLE_REL, SETTLE_FLOOR, FIT_END, END = 0.8 / 256 / 2, 200e-9, 395e-9, 0.2, 10e-9, 850e-9, 3.65e-6

def constants(r):
    wc = 2 * math.pi * r["fc_hz"]
    p2 = wc * math.tan(math.radians(r["pm_deg"]))
    return {"mid": 0.6 + 2 * r["offset_v"], "slope": 1 + r["gain_error"], "out_low": r["out_low_v"], "out_high": r["out_high_v"],
            "wu": wc * math.hypot(wc, p2) / p2, "p2": p2, "slew_up": r["rise_slew_v_per_s"], "slew_down": r["fall_slew_v_per_s"]}

def define(c):
    return "`define OPAMP_MODEL " + ", ".join(f".{k}({v:.9g})" for k, v in c.items())

def edges(t, vin):
    found, level = [], vin[0]
    while True:
        moved = np.nonzero((np.abs(vin - level) > 1e-3) & (t > (found[-1] + 5e-9 if found else -1)))[0]
        if not len(moved):
            return found
        found.append(t[moved[0]])
        level = np.interp(found[-1] + 5e-9, t, vin)

def settling(t, v, te):
    final = np.interp(te + FINAL, t, v)
    out = (t >= te) & (t <= te + FINAL) & (np.abs(v - final) > ERR_V)
    return t[np.nonzero(out)[0][-1]] - te if out.any() else 0.0

def edge_errors(tr, vr, tm, vm, te):
    err = abs(np.interp(te + WINDOW, tm, vm) - np.interp(te + WINDOW, tr, vr))
    return err, settling(tr, vr, te), settling(tm, vm, te)

def judge(err, ts_real, ts_model):
    return err <= ERR_V and abs(ts_model - ts_real) <= max(SETTLE_REL * ts_real, SETTLE_FLOOR)

def check(fit, dirs):
    ok, worst = True, {"fit": [0.0, 0.0], "validation": [0.0, 0.0]}
    for d in map(Path, dirs):
        real, model = np.loadtxt(d / "wave.txt"), np.loadtxt(d / "model.txt")
        tr, vin, vr, tm, vm = real[:, 0], real[:, 1], real[:, 3], model[:, 0], model[:, 1]
        if min(tr[-1], tm[-1]) < END * (1 - 1e-3):
            ok = False
            print(f"{d.name}: FAIL, a run ended at {min(tr[-1], tm[-1]):.4g} s, before the stimulus's {END:g} s")
            continue
        for k, te in enumerate(edges(tr, vin)):
            group = "fit" if d.name in fit and te < FIT_END else "validation"
            err, ts_real, ts_model = edge_errors(tr, vr, tm, vm, te)
            passed = judge(err, ts_real, ts_model)
            ok &= passed
            step = np.interp(te + FINAL, tr, vr) - np.interp(te - 1e-9, tr, vr)
            worst[group][0] = max(worst[group][0], err)
            worst[group][1] = max(worst[group][1], abs(ts_model - ts_real))
            print(f"{d.name} edge {k} at {te:.4g} s, output step {step:+.4g} V, {group}: error_200ns_v {err:.3g} settle_s transistor {ts_real:.4g} model {ts_model:.4g}: {'ok' if passed else 'FAIL'}")
    for group, (err, ts) in worst.items():
        print(f"{group} set: worst error_200ns_v {err:.3g} (limit {ERR_V:.4g}), worst settling difference {ts:.3g} s")
    print("model matches the transistors within the stated error" if ok else "model misses the stated error")
    return ok

if __name__ == "__main__":
    mode, *args = sys.argv[1:]
    if mode == "define":
        print(define(constants(parse(args[0]))))
        sys.exit(0)
    sys.exit(0 if check(args[0].split(), args[1:]) else 1)
