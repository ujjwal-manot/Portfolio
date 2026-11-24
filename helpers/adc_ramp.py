# Writes and reads the ADC's transistor ramp around its major code transitions: pwl writes ramp.inc, a staircase vin that holds each level through its sample (samples at 8.45 us plus whole microseconds, after the 8 calibration frames) and steps 1/8 LSB halfway through the bit trials, two settling samples at mid scale and then 41 levels from 2.5 LSB below to 2.5 LSB above each of codes 64, 128 and 192; transitions reads ramp.txt, checks every scheduled sample came back and that vin at each sampling edge is the level scheduled for it, and gives each code edge it crossed (between the last level coded below it and the first coded at or above it, in LSB of 3.125 mV from vref_lo, against the ideal edge at the code number), refusing a code that goes back down on a rising ramp: python3 adc_ramp.py pwl ramp.inc | transitions supply ramp.txt.
import sys
from adc_results import codes_from_run

LO, LSB, STEP, FIRST, LEAD = 0.2, 0.8 / 256, 1 / 8, 8.45e-6, 2
CENTRES = (64, 128, 192)

def levels():
    xs = [128.0] * LEAD
    for c in CENTRES:
        xs += [c - 2.5 + STEP * i for i in range(41)]
    return xs

def pwl():
    xs, points = levels(), []
    for m, x in enumerate(xs):
        v = LO + x * LSB
        start, end = FIRST + (m - 0.5) * 1e-6 + 5e-9, FIRST + (m + 0.5) * 1e-6 - 5e-9
        points += [(0.0 if m == 0 else start, v), (end, v)]
    body = " ".join(f"{t:.9g} {v:.9g}" for t, v in points)
    return f".param ramp_end={FIRST + len(xs) * 1e-6 + 1e-6:.9g}\nVIN vin 0 pwl({body})\n"

def sampled_inputs(path, supply):
    rows = [[float(v) for v in l.split()][1::2] for l in open(path) if l.strip()]
    return [rows[i - 1][10] for i in range(1, len(rows)) if rows[i - 1][9] > supply / 2 >= rows[i][9]]

def transitions(path, supply):
    xs, codes = levels(), codes_from_run(path, supply)
    if len(codes) < len(xs):
        raise ValueError(f"{path}: {len(codes)} codes, the ramp schedules {len(xs)}")
    held = sampled_inputs(path, supply)[8:8 + len(xs)]
    worst = max(abs((v - LO) / LSB - x) for v, x in zip(held, xs))
    if len(held) < len(xs) or worst > 0.05:
        raise ValueError(f"{path}: vin at the sampling edges is {worst:.3f} LSB off the schedule")
    edges, problems = [], []
    for w, c in enumerate(CENTRES):
        a = LEAD + 41 * w
        pairs = list(zip(xs[a:a + 41], codes[a:a + 41]))
        for a, b in zip(pairs, pairs[1:]):
            if b[1] < a[1]:
                problems.append(f"{path}: code fell from {a[1]} to {b[1]} at {b[0]:.3f} LSB on a rising ramp")
        for k in range(pairs[0][1] + 1, pairs[-1][1] + 1):
            below = max(x for x, code in pairs if code < k)
            above = min(x for x, code in pairs if code >= k)
            edges.append((k, (below + above) / 2, above - below))
    return edges, problems

if __name__ == "__main__":
    mode, args = sys.argv[1], sys.argv[2:]
    if mode == "pwl":
        open(args[0], "w").write(pwl())
        sys.exit(0)
    supply, fails = float(args[0]), []
    for path in args[1:]:
        edges, problems = transitions(path, supply)
        for k, x, gap in edges:
            print(f"{path}: edge {k - 1} to {k} at {x:.4f} LSB, {x - k:+.4f} LSB from ideal, resolved to {gap:.3f} LSB")
        widths = [(k, b - a - 1) for (k, a, _), (j, b, _) in zip(edges, edges[1:]) if j == k + 1]
        for k, w in widths:
            print(f"{path}: code {k} width dnl {w:+.4f} LSB")
        fails += problems
    for f in fails:
        print("FAIL " + f)
    print("every check passes" if not fails else f"{len(fails)} failures")
    sys.exit(1 if fails else 0)
