# Reads the ADC's top-plate offset trim results: trim_levels.txt (top plate minus vcm for each of the 128 trim codes, and eight pairs of top-plate readings a DAC LSB apart, whose mean difference is one DAC LSB at the plate, any missing or nan value refused) gives the trim step, its DNL in steps, monotonicity and its reach either side of the zero code 63 in LSB, checked against a step of at most 0.25 LSB, no step at or below zero, and a reach of at least 7.0 LSB each way (the 4.19 LSB worst comparator Monte Carlo offset, up to 10% more once the trim and parasitics load the plate, plus the 2.02 LSB uncalibrated offset seen at ff 27 C, plus 0.4 LSB for temperature and supply drift); a conversion record (convert.txt with the trim bits as its last seven columns) gives the trim code calibration settled on, and fails if the code moves after calibration: python3 adc_trim.py levels|code ...
import math, statistics, sys

ZERO, STEP_MAX, REACH = 63, 0.25, 7.0

def read_levels(path):
    shifts, pairs = {}, {}
    for line in open(path).read().splitlines()[1:]:
        if line.startswith("zero is real:"):
            continue
        key, *values = line.split()
        values = [float(v) for v in values]
        if any(not math.isfinite(v) for v in values):
            raise ValueError(f"{path}: {key} is not a number")
        if key.startswith("pair_"):
            pairs[int(key[5:])] = values[1] - values[0]
        else:
            shifts[int(key)] = values[0]
    dac_step = statistics.mean(pairs.values()) if sorted(pairs) == list(range(8)) else None
    if sorted(shifts) != list(range(128)) or dac_step is None or not dac_step > 0:
        raise ValueError(f"{path}: needs 128 trim codes and 8 DAC step pairs with a positive mean, found {len(shifts)} codes and {sorted(pairs)}")
    return [shifts[c] for c in range(128)], dac_step

def levels(path):
    shifts, dac_step = read_levels(path)
    steps = [b - a for a, b in zip(shifts, shifts[1:])]
    mean = (shifts[-1] - shifts[0]) / 127
    r = {"step_lsb": mean / dac_step, "dnl_min": min(steps) / mean - 1, "dnl_max": max(steps) / mean - 1,
         "smallest_step_lsb": min(steps) / dac_step, "low_lsb": (shifts[0] - shifts[ZERO]) / dac_step, "high_lsb": (shifts[-1] - shifts[ZERO]) / dac_step,
         "dac_step_v": dac_step}
    problems = []
    if r["step_lsb"] > STEP_MAX:
        problems.append(f"{path}: trim step {r['step_lsb']:.4f} LSB, more than {STEP_MAX}")
    if min(steps) <= 0:
        problems.append(f"{path}: trim not monotonic, smallest step {r['smallest_step_lsb']:.4f} LSB at code {steps.index(min(steps))}")
    if -r["low_lsb"] < REACH or r["high_lsb"] < REACH:
        problems.append(f"{path}: trim reaches {r['low_lsb']:.3f} to {r['high_lsb']:.3f} LSB, less than {REACH} each way")
    r["problems"] = problems
    return r

def settled_code(path, supply):
    rows = [[float(v) for v in l.split()][1::2] for l in open(path) if l.strip()]
    codes = [sum(1 << (6 - j) for j in range(7) if r[-7 + j] > supply / 2) for r in rows]
    valid = [i for i in range(1, len(rows)) if rows[i][0] > supply / 2 >= rows[i - 1][0]]
    if not valid:
        raise ValueError(f"{path}: no code was delivered")
    after = set(codes[valid[0]:])
    if len(after) != 1:
        raise ValueError(f"{path}: the trim code moved after calibration: {sorted(after)}")
    return after.pop()

if __name__ == "__main__":
    mode, args, fails = sys.argv[1], sys.argv[2:], []
    if mode == "levels":
        for path in args:
            r = levels(path)
            print(f"{path}: trim step {r['step_lsb']:.4f} LSB, dnl {r['dnl_min']:.3f} to {r['dnl_max']:.3f} steps, smallest step {r['smallest_step_lsb']:.4f} LSB, reach {r['low_lsb']:.3f} to {r['high_lsb']:.3f} LSB from code {ZERO}, DAC LSB at the top plate {r['dac_step_v'] * 1e3:.4f} mV")
            fails += r["problems"]
    elif mode == "code":
        supply = float(args[0])
        for path in args[1:]:
            print(f"{path}: calibration settled on trim code {settled_code(path, supply)}")
    for f in fails:
        print("FAIL " + f)
    print("every check passes" if not fails else f"{len(fails)} failures")
    sys.exit(1 if fails else 0)
