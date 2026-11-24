# Checks adc_supply on made-up records: the supply current and its 50 ns peak come back from an energy ramp, a current record gives its peak and the charge in each half clock period and is refused when cut short or holding nan, the references are read at each comparator clock rise, and a missing power in measure.txt is refused.
import pytest
from adc_supply import current, wave, refs, measure

def test_current_from_energy_ramp(tmp_path):
    lines = []
    for k in range(400):
        t = k * 5e-8
        e = 1.2 * 100e-6 * t + (1e-13 if t >= 15e-6 else 0)
        values = [0] * 13 + [e]
        lines.append(" ".join(f"{t} {v}" for v in values))
    (tmp_path / "c.txt").write_text("\n".join(lines) + "\n")
    (tmp_path / "m.txt").write_text("p_vdd_w 1.2e-4 p_hi_w 2e-6 p_lo_w -1e-7 p_cm_w 0 fin_hz 39062.5\n")
    r = current(1.2, tmp_path / "c.txt", tmp_path / "m.txt")
    assert abs(r["i_vdd_a"] - 100e-6) < 1e-12 and abs(r["i_cal_a"] - 100e-6) < 1e-9
    assert abs(r["peak_50ns_a"] - (100e-6 + 1e-13 / 5e-8 / 1.2)) < 1e-9

def test_missing_power_is_refused(tmp_path):
    (tmp_path / "m.txt").write_text("p_vdd_w 1e-4 fin_hz 39062.5\n")
    with pytest.raises(ValueError):
        measure(tmp_path / "m.txt")

def test_wave_peak_and_edge_charge(tmp_path):
    rows = [(k * 1e-9, 1e-3 if k % 50 == 0 else 0.0) for k in range(20001)]
    (tmp_path / "w.txt").write_text("".join(f"{t} {i}\n" for t, i in rows))
    r = wave(tmp_path / "w.txt", 20e-6)
    assert r["peak_a"] == 1e-3 and abs(r["edge_charge_mean_c"] - 1e-12) < 1e-13
    with pytest.raises(ValueError, match="should reach"):
        wave(tmp_path / "w.txt", 25e-6)
    (tmp_path / "n.txt").write_text("0 0\n1e-9 nan\n")
    with pytest.raises(ValueError, match="nan"):
        wave(tmp_path / "n.txt", 1e-9)

def test_refs_at_clock_rises(tmp_path):
    lines = []
    for k in range(40):
        t = k * 1e-8
        clk = 1.2 if k % 10 >= 5 else 0.0
        hi = 1.0 + (3.125e-3 if k == 15 else 0.0)
        lines.append(f"{t} {clk} {t} {hi} {t} 0.6 {t} 0.2")
    (tmp_path / "r.txt").write_text("\n".join(lines) + "\n")
    r = refs(tmp_path / "r.txt", 1.2)
    assert r["decisions"] == 4 and abs(r["vref_hi - vref_lo"][0] - 0.5) < 1e-6 and r["vcm"][0] == 0
