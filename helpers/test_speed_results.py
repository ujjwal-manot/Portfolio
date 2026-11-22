# Checks the cell speed reader on made-up sweeps: the slowdown at each supply is the worst over the slow-process corners and the three cells against the slow library's own point (ss, 125 C, 1.08 V), and the transistor sweep must reproduce the library's slow/typ and fast/typ delay ratios to within 5%.
from speed_results import read_sweep, slowdown, ratio_errors, cold_read_slowdown

def sweep(tmp_path, name, scale):
    rows = "vdd inv_s nand_s nor_s\n" + "".join(f"{v / 100:.2f} {scale * 1e-10 * 1.2 / (v / 100)} {scale * 1.4e-10 * 1.2 / (v / 100)} {scale * 1.6e-10 * 1.2 / (v / 100)}\n" for v in range(80, 134, 2))
    path = tmp_path / f"speed_{name}.txt"
    path.write_text(rows)
    return path

def test_sweeps_are_read_by_supply(tmp_path):
    s = read_sweep(sweep(tmp_path, "tt_25", 1.0))
    assert abs(s[1.2]["inv_s"] - 1e-10) < 1e-20 and len(s) == 27

def test_slowdown_takes_the_worst_slow_corner_and_cell(tmp_path):
    sweeps = {"ss_125": read_sweep(sweep(tmp_path, "ss_125", 1.5)), "ss_m40": read_sweep(sweep(tmp_path, "ss_m40", 1.2))}
    sweeps["ss_m40"][0.9]["nor_s"] *= 1.5
    s = slowdown(sweeps)
    assert abs(s[1.08] - 1.0) < 1e-9
    assert abs(s[0.9] - (1.2 * 1.6e-10 * 1.2 / 0.9 * 1.5) / (1.5 * 1.6e-10 * 1.2 / 1.08)) < 1e-9

def test_library_ratios_must_be_reproduced(tmp_path):
    sweeps = {c: read_sweep(sweep(tmp_path, c, k)) for c, k in (("tt_25", 1.0), ("ss_125", 1.5), ("ff_m40", 0.7))}
    lib = {"typ": {"inv_s": 1e-10, "nand_s": 1.4e-10, "nor_s": 1.6e-10}}
    lib["slow"] = {k: v * 1.5 * 1.2 / 1.08 for k, v in lib["typ"].items()}
    lib["fast"] = {k: v * 0.7 * 1.2 / 1.32 for k, v in lib["typ"].items()}
    assert max(abs(e) for e in ratio_errors(sweeps, lib).values()) < 1e-9
    lib["slow"]["nor_s"] *= 1.06
    assert abs(ratio_errors(sweeps, lib)[("slow", "nor_s")] - (1 / 1.06 - 1)) < 1e-9

def test_cold_read_slowdown_is_hot_current_over_cold(tmp_path):
    hot, cold = tmp_path / "read_ss_125.txt", tmp_path / "read_ss_m40.txt"
    hot.write_text("vdd_v read_a\n1.08 3.0e-5\n1.2 4.0e-5\n")
    cold.write_text("vdd_v read_a\n1.08 2.5e-5\n1.2 5.0e-5\n")
    s = cold_read_slowdown(hot, cold)
    assert abs(s[1.08] - 1.2) < 1e-9 and abs(s[1.2] - 0.8) < 1e-9
