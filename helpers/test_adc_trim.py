# Checks adc_trim on made-up trim level files and conversion records: an even trim passes and reports its step and reach, a reversed step, a coarse step, a short reach, a missing code or step pair and a nan each fail, and the settled trim code is read from the last seven columns and refused if it moves after the first delivered code.
import pytest
from adc_trim import levels, settled_code

def write_levels(tmp_path, shifts, dac_step=3e-3, name="t.txt"):
    p = tmp_path / name
    p.write_text("code shift_v\n" + "".join(f"{c} {v}\n" for c, v in enumerate(shifts)) + ("".join(f"pair_{k} {2e-4} {2e-4 + dac_step}\n" for k in range(8)) if dac_step else ""))
    return p

def even(step):
    return [(c - 63) * step + 2e-4 for c in range(128)]

def test_even_trim_passes(tmp_path):
    r = levels(write_levels(tmp_path, even(0.4e-3)))
    assert r["problems"] == []
    assert abs(r["step_lsb"] - 0.4 / 3) < 1e-9
    assert abs(r["low_lsb"] + 63 * 0.4 / 3) < 1e-9 and abs(r["high_lsb"] - 64 * 0.4 / 3) < 1e-9

def test_reversed_step_fails(tmp_path):
    s = even(0.4e-3)
    s[64] = s[63] - 1e-5
    assert any("not monotonic" in p for p in levels(write_levels(tmp_path, s))["problems"])

def test_coarse_step_and_short_reach_fail(tmp_path):
    assert any("more than 0.25" in p for p in levels(write_levels(tmp_path, even(0.9e-3)))["problems"])
    assert any("less than 7.0" in p for p in levels(write_levels(tmp_path, even(0.2e-3)))["problems"])

def test_missing_code_or_step_is_refused(tmp_path):
    with pytest.raises(ValueError):
        levels(write_levels(tmp_path, even(0.4e-3)[:127]))
    with pytest.raises(ValueError):
        levels(write_levels(tmp_path, even(0.4e-3), dac_step=None))
    s = even(0.4e-3)
    s[5] = float("nan")
    with pytest.raises(ValueError, match="not a number"):
        levels(write_levels(tmp_path, s))

def record(tmp_path, trims, valid_at=2):
    lines = []
    for i, t in enumerate(trims):
        values = [1.2 if i >= valid_at else 0] + [0] * 13 + [1.2 if t >> (6 - j) & 1 else 0 for j in range(7)]
        lines.append(" ".join(f"{i * 5e-8} {v}" for v in values))
    p = tmp_path / "convert.txt"
    p.write_text("\n".join(lines) + "\n")
    return p

def test_settled_code(tmp_path):
    assert settled_code(record(tmp_path, [64, 80, 75, 75, 75]), 1.2) == 75
    with pytest.raises(ValueError, match="moved"):
        settled_code(record(tmp_path, [64, 80, 75, 76, 75]), 1.2)
