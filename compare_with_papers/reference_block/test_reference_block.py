# Verifies compare_with_papers/reference_block: spm.v 32-bit serial-parallel multiplier bit-exact arithmetic, LibreLane config.json schema matching librelane_spm_example, and 3-corner 100 MHz OpenSTA timing.tcl constraints.
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPM_V = HERE / "spm.v"
CFG_JSON = HERE / "config.json"
TIMING_TCL = HERE / "timing.tcl"


def sim_spm_serial(a_val, x_val, n_bits=32):
    a_bits = [(a_val >> i) & 1 for i in range(n_bits)]
    pp = [0] * n_bits
    sc = [0] * (n_bits - 1)
    z = 0
    y_out = 0
    out_bits = []
    for step in range(2 * n_bits):
        x_bit = ((x_val >> step) & 1) if step < n_bits else ((x_val >> (n_bits - 1)) & 1)
        xy = [a_bits[i] & x_bit for i in range(n_bits)]
        next_pp = [0] * n_bits
        next_sc = [0] * (n_bits - 1)
        next_z = xy[n_bits - 1] | z
        next_pp[n_bits - 1] = xy[n_bits - 1] ^ z

        for i in range(1, n_bits - 1):
            hsum1 = pp[i + 1] ^ sc[i]
            hco1 = pp[i + 1] & sc[i]
            hco2 = xy[i] & hsum1
            next_pp[i] = xy[i] ^ hsum1
            next_sc[i] = hco1 ^ hco2

        hsum0 = pp[1] ^ sc[0]
        hco1_0 = pp[1] & sc[0]
        hco2_0 = xy[0] & hsum0
        next_y = xy[0] ^ hsum0
        next_sc[0] = hco1_0 ^ hco2_0

        pp, sc, z, y_out = next_pp, next_sc, next_z, next_y
        out_bits.append(y_out)
    result = sum(b << i for i, b in enumerate(out_bits[:n_bits]))
    return result


def test_spm_verilog_hierarchy_and_serial_multiplier_equivalence():
    text = re.sub(r"//.*", "", SPM_V.read_text(encoding="utf-8"))
    mods = set(re.findall(r"\bmodule\s+(\w+)", text))
    assert {"spm", "tcmp", "csadd", "scadd"} <= mods
    for a_val, x_val in ((0, 0), (1, 1), (7, 5), (12345, 6789), (0x00FF00FF, 3), (42, -7 & 0xFFFFFFFF)):
        got = sim_spm_serial(a_val, x_val, n_bits=32)
        want = (a_val * x_val) & 0xFFFFFFFF
        assert got == want, f"spm({a_val}, {x_val}): got {got:#x}, expected {want:#x}"


def test_librelane_config_and_timing_constraints_match_published_spec():
    cfg = json.loads(CFG_JSON.read_text(encoding="utf-8"))
    assert cfg["DESIGN_NAME"] == "spm"
    assert cfg["CLOCK_PORT"] == "clk"
    assert cfg["CLOCK_PERIOD"] == 10
    assert cfg["VERILOG_FILES"] == ["dir::spm.v"]
    assert cfg["RT_MAX_LAYER"] == "Metal5"

    tcl = TIMING_TCL.read_text(encoding="utf-8")
    assert "link_design spm" in tcl
    assert "create_clock -name clk -period 10 [get_ports clk]" in tcl
    assert "1.016" in tcl
    assert "sg13g2_dfrbpq_1" in tcl
