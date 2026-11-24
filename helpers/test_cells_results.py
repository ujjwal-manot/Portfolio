# Tests cells_results.py: extracted-against-schematic checks for the switch unit, comparator and array pass on good numbers and fail on a missing or unreadable value, a bisection that does not follow its own steps, or a number past its limit.
import subprocess, sys
from pathlib import Path

HERE = Path(__file__).parent

def run(args):
    return subprocess.run([sys.executable, str(HERE / "cells_results.py"), *map(str, args)], capture_output=True, text=True)

def unit(path, i_on="3e-4", t_on="2e-9", i_off="1e-12"):
    path.write_text(f"unit i_on_a {i_on} i_off_a {i_off} t_on_s {t_on} t_off_s 3e-9 i_vin_on_a -{i_on} i_vin_off_a -1.1e-12\n")

def test_unit(tmp_path):
    unit(tmp_path / "unit_sch_tt_27_1v2_3v3.txt")
    unit(tmp_path / "unit_ext_tt_27_1v2_3v3.txt", i_on="2.97e-4")
    assert run(["unit", tmp_path / "unit_ext_tt_27_1v2_3v3.txt"]).returncode == 0
    unit(tmp_path / "unit_ext_tt_27_1v2_3v3.txt", i_on="2.9e-4")
    assert run(["unit", tmp_path / "unit_ext_tt_27_1v2_3v3.txt"]).returncode == 1
    unit(tmp_path / "unit_ext_tt_27_1v2_3v3.txt", t_on="$&t_on")
    assert run(["unit", tmp_path / "unit_ext_tt_27_1v2_3v3.txt"]).returncode == 1
    unit(tmp_path / "unit_ext_tt_27_1v2_3v3.txt", t_on="11e-9")
    assert run(["unit", tmp_path / "unit_ext_tt_27_1v2_3v3.txt"]).returncode == 1
    unit(tmp_path / "unit_ext_tt_27_1v2_3v3.txt", i_off="3e-6")
    assert run(["unit", tmp_path / "unit_ext_tt_27_1v2_3v3.txt"]).returncode == 1
    assert run(["unit", tmp_path / "unit_ext_ss_125_1v08_3v6.txt"]).returncode == 1

def bisect(threshold, vdd=1.2, steps=15, stuck=False):
    lines = []
    for first in ("-50e-3", "50e-3"):
        lo, hi = -20e-3, 20e-3
        for _ in range(steps):
            mid = (lo + hi) / 2
            high = mid > threshold
            lines.append(f"step {first} {0.0 if stuck else mid:.6E} {vdd if high else 1e-7:.6E}")
            lo, hi = (lo, mid) if high else (mid, hi)
    return lines

def cmp(path, threshold=2e-4, delay="1.2e-9", **kw):
    path.write_text("\n".join(["cmp"] + bisect(threshold, **kw) + [f"delay 1e-3 {delay}", "delay -1e-3 1.3e-9"]) + "\n")

def test_cmp(tmp_path):
    sch, ext = tmp_path / "cmp_sch_tt_27_1v2.txt", tmp_path / "cmp_ext_tt_27_1v2.txt"
    cmp(sch, threshold=1e-6)
    cmp(ext)
    good = run(["cmp", ext])
    assert good.returncode == 0, good.stdout
    assert "0.200 mV" in good.stdout
    cmp(ext, threshold=1.5e-3)
    assert run(["cmp", ext]).returncode == 1
    cmp(ext, steps=14)
    assert run(["cmp", ext]).returncode == 1
    cmp(ext, stuck=True)
    assert run(["cmp", ext]).returncode == 1
    cmp(ext, delay="$&t")
    assert run(["cmp", ext]).returncode == 1
    cmp(ext)
    cmp(sch, delay="12e-9")
    assert run(["cmp", ext]).returncode == 1

def test_array(tmp_path):
    (tmp_path / "array_sch_tt_27_1v2_3v3.txt").write_text("array i_rail_a 4.0e-2 i_vin_a -4.0e-2\n")
    (tmp_path / "array_ext_tt_27_1v2_3v3.txt").write_text("array i_rail_a 3.95e-2 i_vin_a -3.95e-2\n")
    assert run(["array", tmp_path / "array_ext_tt_27_1v2_3v3.txt"]).returncode == 0
    (tmp_path / "array_ext_tt_27_1v2_3v3.txt").write_text("array i_rail_a 3.9e-2 i_vin_a -3.9e-2\n")
    assert run(["array", tmp_path / "array_ext_tt_27_1v2_3v3.txt"]).returncode == 1
    (tmp_path / "array_ext_tt_27_1v2_3v3.txt").write_text("array i_rail_a 4.2e-2 i_vin_a -4.2e-2\n")
    assert run(["array", tmp_path / "array_ext_tt_27_1v2_3v3.txt"]).returncode == 1
    (tmp_path / "array_ext_tt_27_1v2_3v3.txt").write_text("array i_rail_a nan i_vin_a -3.9e-2\n")
    assert run(["array", tmp_path / "array_ext_tt_27_1v2_3v3.txt"]).returncode == 1
