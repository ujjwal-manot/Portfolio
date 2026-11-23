# Checks adc_ramp on a made-up conversion record: the staircase holds each level through its sample and steps halfway between samples, an ideal ramp gives every edge on its code number to within the 1/8 LSB step, a shifted one moves every edge by the shift, a missing sample or a misaligned input is refused, and a code that falls on the rising ramp fails.
import math, re
import pytest
from adc_ramp import pwl, levels, transitions, FIRST, LO, LSB

def record(tmp_path, shift=0.0, drop=0, lag=0.0, swap=None):
    xs = levels()
    codes = [min(255, max(0, math.floor(x + shift))) for x in xs]
    if swap is not None:
        codes[swap], codes[swap + 1] = codes[swap + 1], codes[swap]
    lines, t = [], 0.0
    frames = 8 + len(xs) - drop
    for f in range(frames + 1):
        for step in range(20):
            t = 0.45e-6 + (f - 1) * 1e-6 + step * 5e-8
            samp = 1.2 if step >= 18 else 0.0
            m = f - 8
            x = xs[min(max(m, 0), len(xs) - 1)] + lag
            valid = 1.2 if 8 < f and step < 2 else 0.0
            code = codes[f - 9] if 8 < f <= 8 + len(xs) - drop else 0
            bits = [1.2 if code >> (7 - j) & 1 else 0.0 for j in range(8)]
            values = [valid] + bits + [samp, LO + x * LSB, 0.6, 0.6] + [0.0] * 7
            lines.append(" ".join(f"{t:.9g} {v}" for v in values))
    p = tmp_path / "ramp.txt"
    p.write_text("\n".join(lines) + "\n")
    return p

def test_pwl_holds_each_level_through_its_sample():
    text = pwl()
    end = float(re.search(r"ramp_end=(\S+)", text).group(1))
    nums = [float(v) for v in re.search(r"pwl\((.*)\)", text).group(1).split()]
    points = list(zip(nums[::2], nums[1::2]))
    assert len(points) == 2 * len(levels()) and end > points[-1][0]
    for m, x in enumerate(levels()):
        a, b = points[2 * m], points[2 * m + 1]
        assert a[1] == b[1] and abs(a[1] - (LO + x * LSB)) < 1e-9
        assert a[0] < FIRST + m * 1e-6 < b[0]

def test_ideal_and_shifted_ramps(tmp_path):
    edges, problems = transitions(record(tmp_path), 1.2)
    assert problems == [] and len(edges) == 15
    assert all(abs(x - k) <= 1 / 16 + 1e-9 for k, x, _ in edges)
    edges, _ = transitions(record(tmp_path, shift=0.5), 1.2)
    assert all(abs(x - k + 0.5) <= 1 / 16 + 1e-9 for k, x, _ in edges)

def test_missing_or_misaligned_samples_are_refused(tmp_path):
    with pytest.raises(ValueError, match="codes"):
        transitions(record(tmp_path, drop=3), 1.2)
    with pytest.raises(ValueError, match="off the schedule"):
        transitions(record(tmp_path, lag=0.5), 1.2)

def test_falling_code_fails(tmp_path):
    edges, problems = transitions(record(tmp_path, swap=2 + 10), 1.2)
    assert problems and "fell" in problems[0]
