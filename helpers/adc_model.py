# Fits, validates and uses the ADC's real-number model (adc_model.sv run by Verilator through tests/model_tb.sv), with the metric and limits fixed before any fit: each table takes the DAC levels from that corner's transistor dac_levels run and the trim shifts from its trim_levels run (both turned into volts at the input with the measured top-plate gain), and only two numbers are fitted, both at tt 27 C 1.2 V: the calibration-mode offset from the trim code the transistor calibration settled on, and the conversion-mode offset from the transistor ramp's code edges (fit error: every ramp edge within 0.25 LSB); validation runs the model on stimuli and corners the fit never saw (the tt 27 C tone, and the tone at every other transistor conversion corner, using that process's 27 C tables where no table was run at the corner itself) and fails unless every code is within 1 of the transistor's, the trim code within 2, ENOB within 0.1 bit, offset within 0.25 LSB and gain error within 0.5 LSB; then the model gives the sine-histogram DNL and INL at tt 27 C (IEEE 1241 code density, 2^18 samples of an overranged sine, whose ends beyond the 0.2 to 1.0 V range the transistor runs never checked) and at the five process corners, and a Monte Carlo yield at tt 27 C 1.2 V over 100 dies (die i takes DAC and trim mismatch tables i mod 20 and the comparator offset from Monte Carlo run i) against chip.md's offset, gain, ENOB, DNL and INL limits with a calibrated trim off its rails, with the one-sided 95% lower bound: python3 adc_model.py all binary build_dir results_dir.
import math, statistics, subprocess, sys
from pathlib import Path
from adc_results import codes_from_run, check_conversion
from adc_trim import read_levels, settled_code
from adc_ramp import levels as ramp_levels, transitions, LEAD
from adc_spectrum import spectrum
from adc_histogram import code_density
from analog_results import lower_bound

LO, LSB, N, K, FS = 0.2, 0.8 / 256, 128, 5, 1e6
AMP = 0.4 * 10 ** (-0.5 / 20)
LIMIT = {"code": 1, "trim": 2, "enob": 0.1, "offset_lsb": 0.25, "gain_error_lsb": 0.5, "fit_edge_lsb": 0.25}
SPEC = {"offset_lsb": 1.0, "gain_error_lsb": 2.0, "enob": 7.5, "dnl": 0.5, "inl": 1.0}
HIST_N, HIST_K, HIST_AMP = 2 ** 18, 1031, 0.41
VOLT = {"min": 1.16, "nom": 1.2, "hi": 1.32}

def gain(trim_path):
    shifts, step = read_levels(trim_path)
    return shifts, step * 257 / 0.8

def table(levels_path, trim_path, offset_v, offset_cal_v, out):
    err = [float(l.split()[1]) for l in open(levels_path).read().splitlines()[1:]]
    if len(err) != 256 or any(not math.isfinite(e) for e in err):
        raise ValueError(f"{levels_path}: needs 256 finite DAC levels")
    shifts, g = gain(trim_path)
    level = [LO + c * LSB + err[c] / g for c in range(256)]
    shift = [(s - shifts[63]) / g for s in shifts]
    Path(out).write_text(f"{offset_v!r} {offset_cal_v!r}\n" + "".join(f"{v!r}\n" for v in level + shift))
    return level, shift

def run(binary, table_path, out, n, **stim):
    args = [str(binary), f"+table={table_path}", f"+n={n}", f"+out={out}"] + [f"+{k}={v}" for k, v in stim.items()]
    subprocess.run(args, check=True, capture_output=True, text=True)
    lines = Path(out).read_text().split("\n")
    trim = int(lines[0].split()[1])
    codes = [int(v) for v in lines[1:] if v.strip()]
    if len(codes) != n:
        raise ValueError(f"{out}: {len(codes)} codes, asked for {n}")
    return trim, codes

def metrics(codes):
    r = spectrum(codes, K)
    x = [float(c) for c in codes]
    amplitude = 2 * abs(sum(v * complex(math.cos(2 * math.pi * K * i / N), -math.sin(2 * math.pi * K * i / N)) for i, v in enumerate(x))) / N
    return {"enob": r["enob"], "offset_lsb": statistics.mean(x) - 127.5, "gain_error_lsb": (amplitude / (AMP / LSB) - 1) * 256}

def fit(binary, build, results):
    shifts, g = gain(results / "trim_tt_27_nom.txt")
    t_cal = settled_code(results / "convert_tt_27_nom.txt", 1.2)
    _, shift = table(results / "levels_tt_27_nom.txt", results / "trim_tt_27_nom.txt", 0.0, 0.0, build / "zero.txt")
    if not 0 < t_cal < 127:
        raise ValueError(f"transistor calibration settled on rail code {t_cal}")
    offset_cal = (shift[t_cal] + shift[t_cal + 1]) / 2
    level, _ = table(results / "levels_tt_27_nom.txt", results / "trim_tt_27_nom.txt", 0.0, offset_cal, build / "zero.txt")
    ramp = results / "ramp_tt_27_nom.txt"
    t_ramp = settled_code(ramp, 1.2)
    edges, problems = transitions(ramp, 1.2)
    if problems:
        raise ValueError("; ".join(problems))
    each = [level[k] + shift[t_ramp] - (LO + x * LSB) for k, x, _ in edges]
    offset = statistics.mean(each)
    residual = [(o - offset) / LSB for o in each]
    return offset, offset_cal, t_cal, t_ramp, residual

def main(binary, build, results):
    binary, build, results = Path(binary).resolve(), Path(build), Path(results)
    build.mkdir(parents=True, exist_ok=True)
    fails = []
    offset, offset_cal, t_cal, t_ramp, residual = fit(binary, build, results)
    print(f"fit at tt_27_nom: calibration-mode offset {offset_cal / LSB:+.4f} LSB from the transistor trim code {t_cal}; conversion-mode offset {offset / LSB:+.4f} LSB from {len(residual)} transistor ramp edges (trim code {t_ramp})")
    print(f"fit error: ramp edges rms {math.sqrt(statistics.mean(r * r for r in residual)):.4f} LSB, worst {max(residual, key=abs):+.4f} LSB")
    if max(abs(r) for r in residual) > LIMIT["fit_edge_lsb"]:
        fails.append(f"fit: a ramp edge is {max(residual, key=abs):+.4f} LSB from the model, beyond {LIMIT['fit_edge_lsb']}")
    table(results / "levels_tt_27_nom.txt", results / "trim_tt_27_nom.txt", offset, offset_cal, results / "model_table_tt_27_nom.txt")
    xs = ramp_levels()
    (build / "ramp_levels.txt").write_text("".join(f"{LO + x * LSB!r}\n" for x in xs))
    trim, codes = run(binary, results / "model_table_tt_27_nom.txt", build / "ramp_codes.txt", len(xs), stim="ramp", levels=build / "ramp_levels.txt")
    tr = codes_from_run(results / "ramp_tt_27_nom.txt", 1.2)[:len(xs)]
    print(f"model ramp at tt_27_nom (the fit stimulus): trim {trim} against {t_ramp}, codes differ by at most {max(abs(a - b) for a, b in zip(codes, tr))} on {sum(a != b for a, b in zip(codes, tr))} of {len(xs)} samples")
    rows = []
    corners = sorted(p.name[len("convert_"):-4] for p in results.glob("convert_*_*_*.txt"))
    for c in corners:
        proc, temp, volt = c.split("_")
        trim_path = results / f"trim_{c}.txt" if (results / f"trim_{c}.txt").exists() else results / f"trim_{proc}_27_nom.txt"
        tab = build / f"table_{c}.txt"
        table(results / f"levels_{proc}_27_nom.txt", trim_path, offset, offset_cal, tab)
        ref = check_conversion(results / f"convert_{c}.txt", results / f"measure_{c}.txt", VOLT[volt], N)
        if "enob" not in ref:
            fails.append(f"{c}: the transistor conversion has no result: {ref['problems']}")
            continue
        tr = codes_from_run(results / f"convert_{c}.txt", VOLT[volt])
        t_tr = settled_code(results / f"convert_{c}.txt", VOLT[volt])
        trim, codes = run(binary, tab, build / f"tone_{c}.txt", len(tr), stim="tone", amp=AMP, k=K, nfft=N)
        m = metrics(codes[2:2 + N])
        diff = max(abs(a - b) for a, b in zip(codes[2:2 + N], tr[2:2 + N]))
        d = {k: m[k] - ref[k] for k in ("enob", "offset_lsb", "gain_error_lsb")}
        role = "fit corner, other stimulus" if c == "tt_27_nom" else "validation corner"
        rows.append(f"{c} {role.replace(' ', '_').replace(',', '')} trim_model {trim} trim_transistor {t_tr} code_diff_max {diff} enob_model {m['enob']:.4f} enob_transistor {ref['enob']:.4f} offset_model {m['offset_lsb']:.4f} offset_transistor {ref['offset_lsb']:.4f} gain_error_model {m['gain_error_lsb']:.4f} gain_error_transistor {ref['gain_error_lsb']:.4f}")
        print(f"{c} ({role}): trim {trim} against {t_tr}, codes within {diff}, enob {d['enob']:+.4f}, offset {d['offset_lsb']:+.4f} LSB, gain error {d['gain_error_lsb']:+.4f} LSB, model minus transistor")
        if diff > LIMIT["code"] or abs(trim - t_tr) > LIMIT["trim"] or any(abs(d[k]) > LIMIT[k] for k in d):
            fails.append(f"{c}: model outside the validation limits (codes {LIMIT['code']}, trim {LIMIT['trim']}, enob {LIMIT['enob']}, offset {LIMIT['offset_lsb']}, gain error {LIMIT['gain_error_lsb']})")
    (results / "model_validation.txt").write_text("\n".join(rows) + "\n")
    hist_rows = []
    for proc in ("tt", "ss", "ff", "sf", "fs"):
        tab = build / f"table_{proc}_27_nom.txt"
        table(results / f"levels_{proc}_27_nom.txt", results / f"trim_{proc}_27_nom.txt", offset, offset_cal, tab)
        _, codes = run(binary, tab, build / f"hist_{proc}.txt", HIST_N + 2, stim="tone", amp=HIST_AMP, k=HIST_K, nfft=HIST_N)
        h = code_density(codes[2:], 8)
        print(f"model histogram at {proc}_27_nom ({HIST_N} samples, {HIST_AMP} V sine): dnl within {h['max_dnl_lsb']:.4f} LSB, inl within {h['max_inl_lsb']:.4f} LSB, {len(h['missing_codes'])} missing codes")
        if proc == "tt":
            hist_rows = [f"{c} {d:.5f} {i:.5f}" for c, d, i in zip(h["codes"], h["dnl_lsb"], h["inl_lsb"])]
        if h["max_dnl_lsb"] > SPEC["dnl"] or h["max_inl_lsb"] > SPEC["inl"] or h["missing_codes"]:
            fails.append(f"{proc}_27_nom: model histogram beyond chip.md's DNL or INL, or a missing code")
    (results / "model_hist_tt_27_nom.txt").write_text("code dnl_lsb inl_lsb\n" + "\n".join(hist_rows) + "\n")
    offsets = [float(dict(zip(*[iter((results / f"offset_{i}.txt").read().split())] * 2))["offset_v"]) for i in range(1, 101)]
    mc, passed = [], 0
    for i in range(1, 101):
        j = (i - 1) % 20 + 1
        _, g = gain(results / f"trim_mc{j}.txt")
        tab = build / f"table_mc{i}.txt"
        table(results / f"levels_mc{j}.txt", results / f"trim_mc{j}.txt", offset - offsets[i - 1] / g, offset_cal - offsets[i - 1] / g, tab)
        trim, codes = run(binary, tab, build / f"mc_tone_{i}.txt", N + 2, stim="tone", amp=AMP, k=K, nfft=N)
        m = metrics(codes[2:])
        _, hc = run(binary, tab, build / f"mc_hist_{i}.txt", 2 ** 16 + 2, stim="tone", amp=HIST_AMP, k=HIST_K, nfft=2 ** 16)
        h = code_density(hc[2:], 8)
        ok = abs(m["offset_lsb"]) <= SPEC["offset_lsb"] and abs(m["gain_error_lsb"]) <= SPEC["gain_error_lsb"] and m["enob"] >= SPEC["enob"] and h["max_dnl_lsb"] <= SPEC["dnl"] and h["max_inl_lsb"] <= SPEC["inl"] and not h["missing_codes"] and 0 < trim < 127
        passed += ok
        mc.append(f"die {i} levels_mc{j} trim_mc{j} comparator_offset_v {offsets[i - 1]:.6g} trim {trim} enob {m['enob']:.4f} offset_lsb {m['offset_lsb']:.4f} gain_error_lsb {m['gain_error_lsb']:.4f} dnl {h['max_dnl_lsb']:.4f} inl {h['max_inl_lsb']:.4f} {'pass' if ok else 'fail'}")
    (results / "model_mc.txt").write_text("\n".join(mc) + "\n")
    worst = lambda key: max((float(r.split()[r.split().index(key) + 1]) for r in mc), key=abs)
    print(f"model Monte Carlo at tt 27 C 1.2 V with mismatch, 100 dies (20 DAC and trim mismatch tables, 100 comparator offsets): calibrated yield {passed}% against chip.md's offset, gain error, ENOB, DNL and INL, at least {lower_bound(passed, 100):.1%} at 95% confidence; worst offset {worst('offset_lsb'):+.4f} LSB, worst gain error {worst('gain_error_lsb'):+.4f} LSB, worst dnl {worst('dnl'):.4f} LSB, worst inl {worst('inl'):.4f} LSB")
    for f in fails:
        print("FAIL " + f)
    print("every check passes" if not fails else f"{len(fails)} failures")
    return 1 if fails else 0

if __name__ == "__main__":
    sys.exit(main(*sys.argv[2:5]))
