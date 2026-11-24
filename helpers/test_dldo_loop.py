# Checks dldo_loop.py on small hand-made tables: schedule metrics and spec limits, truncated runs, model-against-transistor errors, OpenSTA window parsing, the both-coarse-high check and the comparator offset check.
import math
import pytest
import dldo_loop as d

SCHEDULE = """t_end 3e-06
s0 0 1e-06 100 idle start
s1 1e-06 2e-06 100 active load_up
s2 2e-06 3e-06 110 active dvfs_up
"""
VREF = 1.206

def trace(path, points, step=1e-9):
    rows, t = [], 0.0
    while t <= points[-1][0] + 1e-15:
        v = [v for (t0, v) in points if t0 <= t + 1e-15][-1]
        rows.append(f"{t:.6e} {v:.6f}")
        t += step
    path.write_text("\n".join(rows) + "\n")
    return path

def files(tmp_path, points):
    s = tmp_path / "schedule.txt"
    s.write_text(SCHEDULE)
    r = tmp_path / "ref.inc"
    r.write_text(".param vref_v=1.206\n")
    return s, r, trace(tmp_path / "loop.txt", points)

def test_setpoint():
    assert d.setpoint(100, VREF) == pytest.approx(1.0)
    assert d.setpoint(90, VREF) == pytest.approx(0.9)

def test_good_run_passes(tmp_path):
    s, r, t = files(tmp_path, [(0, 0.0), (0.5e-6, 1.0), (2.0e-6, 1.05), (2.2e-6, 1.1), (3e-6, 1.1)])
    lines, fails = d.loop_report(s, r, t)
    assert fails == []
    m = {x["name"]: x for x in d.metrics(*d.read_schedule(s)[1:], VREF, d.read_trace(t))}
    assert m["s2"]["settle_s"] == pytest.approx(0.2e-6, abs=2e-9)
    assert m["s1"]["mean_v"] == pytest.approx(1.0)
    assert any("s2" in l and "settles" in l for l in lines)

def test_droop_and_ripple_fail(tmp_path):
    points = [(0, 1.0), (1.2e-6, 0.93), (1.3e-6, 1.0)] + [(1.6e-6 + k * 20e-9, 1.0 + (0.02 if k % 2 else -0.02)) for k in range(20)] + [(2.0e-6, 1.1), (3e-6, 1.1)]
    s, r, t = files(tmp_path, points)
    lines, fails = d.loop_report(s, r, t)
    assert any(f.startswith("s1 rail outside the setpoint +-5%") for f in fails)
    assert any(f.startswith("s1 ripple above 3% of the setpoint") for f in fails)

def test_unsettled_and_truncated(tmp_path):
    s, r, t = files(tmp_path, [(0, 1.0), (2e-6, 1.0), (2.5e-6, 1.0)])
    lines, fails = d.loop_report(s, r, t)
    assert any(f.startswith("run ended at") for f in fails)
    s, r, t = files(tmp_path, [(0, 1.0), (2e-6, 1.0), (3e-6, 1.0)])
    lines, fails = d.loop_report(s, r, t)
    assert any(f.startswith("s2 never settles") for f in fails)

def test_compare(tmp_path):
    s, r, t = files(tmp_path, [(0, 1.0), (2.1e-6, 1.1), (3e-6, 1.1)])
    m = tmp_path / "model.txt"
    trace(m, [(0, 1.002), (2.1e-6, 1.1), (3e-6, 1.1)])
    lines, fails = d.compare(s, r, m, t)
    assert fails == []
    trace(m, [(0, 1.01), (2.2e-6, 1.1), (3e-6, 1.1)])
    lines, fails = d.compare(s, r, m, t)
    assert any(f.startswith("s1 mean differs by") for f in fails)
    assert any(f.startswith("s2 transition time differs by") for f in fails)

STA = """window 0 5 25
Sequential             9.53e-03   6.92e-05   1.53e-06   9.60e-03  74.5%
Combinational          9.37e-06   1.35e-05   2.02e-06   2.49e-05   0.2%
Macro                  3.26e-03   0.00e+00   1.58e-06   3.26e-03  25.3%
window 1 25 45
Sequential             9.96e-03   1.59e-04   1.53e-06   1.01e-02  72.6%
Combinational          1.76e-04   3.14e-04   2.03e-06   4.92e-04   3.5%
Macro                  3.33e-03   0.00e+00   1.58e-06   3.34e-03  23.9%
"""

def test_cpu_windows(tmp_path):
    p = tmp_path / "sta.log"
    p.write_text(STA)
    w = d.cpu_windows(p)
    assert [x["cycle"] for x in w] == [0, 1]
    assert w[1]["cells_a"] == pytest.approx((1.01e-2 + 4.92e-4) / 1.2)
    assert w[0]["macro_a"] == pytest.approx(3.26e-3 / 1.2)
    p.write_text(STA + "Warning 1452: clock clk vcd period 13.333 differs from SDC clock period 20.000\n")
    with pytest.raises(ValueError):
        d.cpu_windows(p)

def check_table(tmp_path, far_lo, far_hi, count_after):
    n, rows = 4, []
    for t in (9e-9, 15e-9):
        count = 5 if t < 10e-9 else count_after
        bits = [1.2 * (count >> i & 1) for i in range(8)]
        vals = [0, 0, far_lo, far_hi, 1.2] + bits + bits + [1.2 * (i < count) for i in range(n)]
        rows.append(" ".join(f"{t:.6e} {v}" for v in vals))
    p = tmp_path / "check.txt"
    p.write_text("\n".join(rows) + "\n")
    return p

def test_coarse(tmp_path):
    lines, fails = d.coarse(check_table(tmp_path, 1.2, 1.2, 5), 4, 15e-9)
    assert fails == [] and any("both coarse high" in l for l in lines)
    lines, fails = d.coarse(check_table(tmp_path, 1.2, 1.2, 13), 4, 15e-9)
    assert any(f.startswith("both coarse high moved the count") for f in fails)
    lines, fails = d.coarse(check_table(tmp_path, 1.2, 0, 13), 4, 15e-9)
    assert any(f.startswith("both coarse high never applied") for f in fails)
    lines, fails = d.coarse(check_table(tmp_path, 1.2, 1.2, 5), 4, 900e-9)
    assert any(f.startswith("run ended at") for f in fails)

def test_offsets(tmp_path):
    paths = []
    for k, v in enumerate([0.5e-3, -0.5e-3, 0.4e-3, -0.4e-3]):
        p = tmp_path / f"o{k}.txt"
        p.write_text(f"offset_v {v} hysteresis_v 1e-5 up_v 0 down_v 0")
        paths.append(p)
    lines, fails = d.offsets(paths, 3e-3)
    assert fails == []
    paths[0].write_text("offset_v nan hysteresis_v 1e-5")
    lines, fails = d.offsets(paths, 3e-3)
    assert any(f.startswith("not a number") for f in fails)
    paths[0].write_text("offset_v 9e-3 hysteresis_v 1e-5")
    lines, fails = d.offsets(paths, 3e-3)
    assert any(f.startswith("3 sigma offset above") for f in fails)

def test_unit_inc(tmp_path):
    iv = tmp_path / "iv.txt"
    iv.write_text("0.8 2.0e-4\n1.0 1.9e-4\n1.2 1.7e-4\n")
    dl = tmp_path / "delay.txt"
    dl.write_text("unit t_on_s 1.5e-09 t_off_s 1.0e-09 t_end_s 4e-08\n")
    text = d.unit_inc(iv, dl, 4e-8)
    assert "pwl(x, 0.8, 0.0002, 1, 0.00019, 1.2, 0.00017)" in text
    assert "t_on=1.5e-09" in text and "t_off=1e-09" in text
    dl.write_text("unit t_on_s nan t_off_s 1.0e-09 t_end_s 4e-08\n")
    with pytest.raises(ValueError):
        d.unit_inc(iv, dl, 4e-8)
    assert math.isfinite(d.setpoint(120, VREF))

def test_sense(tmp_path):
    p = tmp_path / "sense.txt"
    row = lambda tap, k: "sense %d " % tap + " ".join(f"{c}_{e} {0.5 + k if c == 'fl' else 0.5} ideal_{c} 0.5" for c in ("fl", "fh", "cl", "ch") for e in "ab") + " fb_a 0.601 fb_b 0.601 ideal_fb 0.6"
    p.write_text("sensing residues\n" + row(90, 0.001) + "\n")
    lines, fails = d.sense([p], 3e-3)
    assert fails == [] and any("90" in l for l in lines)
    p.write_text("sensing residues\n" + row(90, 0.005) + "\n")
    lines, fails = d.sense([p], 3e-3)
    assert any(f.startswith("sensing residue above") for f in fails)
    p.write_text("sensing residues\n" + row(90, 0.0).replace("fb_b 0.601", "fb_b nan") + "\n")
    lines, fails = d.sense([p], 3e-3)
    assert any(f.startswith("not a number") for f in fails)
