# Verifies port-matching across whole_chip_top.sv, rn_analog_models.sv, whole_chip_cosim_top.sv, and test_whole_chip_cocotb.py, plus real-number model error tolerances against chip.md, opamp logs, adc_spectrum.py, and power_manager speed.log.
import ast
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WC = HERE.parent
ROOT = WC.parent.parent
sys.path.insert(0, str(ROOT / "helpers"))
from adc_spectrum import coherent_bin, spectrum

RN_SV = WC / "design" / "rn_analog_models.sv"
TOP_SV = WC / "design" / "whole_chip_top.sv"
COSIM_SV = HERE / "whole_chip_cosim_top.sv"
COCOTB_PY = HERE / "test_whole_chip_cocotb.py"
SPEED_LOG = ROOT / "projects" / "power_manager" / "results" / "speed.log"
OPAMP_CORNERS = ROOT / "projects" / "opamp" / "results" / "corners.log"
OPAMP_MC = ROOT / "projects" / "opamp" / "results" / "mc.log"

EXPECTED_WHOLE_CHIP_TOP_PORTS = {
    "rst_n": ("input", 1),
    "clk_adc": ("input", 1),
    "clk_sys": ("input", 1),
    "comp_out": ("input", 1),
    "dldo_lo": ("input", 1),
    "dldo_hi": ("input", 1),
    "dldo_far_lo": ("input", 1),
    "dldo_far_hi": ("input", 1),
    "droop_alert": ("input", 1),
    "adc_samp": ("output", 1),
    "adc_comp_clk": ("output", 1),
    "adc_dac": ("output", 8),
    "adc_overflow": ("output", 1),
    "dvfs_state": ("output", 2),
    "fir_last": ("output", 32),
    "peak_last": ("output", 32),
    "cpu_sleep": ("output", 1),
    "dldo_on": ("output", 128),
}


def strip_sv_comments(text):
    return re.sub(r"//.*", "", text)


def parse_sv_modules(text):
    clean = strip_sv_comments(text)
    modules = {}
    pat = re.compile(
        r"\bmodule\s+(\w+)\s*(?:#\s*\((.*?)\)\s*)?\((.*?)\)\s*;(.*?)\bendmodule\b",
        re.S,
    )
    for m in pat.finditer(clean):
        name, param_blk, port_blk, body = m.group(1), m.group(2) or "", m.group(3), m.group(4)
        params = {}
        for pm in re.finditer(r"parameter\s+(?:real|int)\s+(\w+)\s*=\s*([0-9eE.+\-]+)", param_blk):
            val = pm.group(2)
            params[pm.group(1)] = float(val) if ("." in val or "e" in val.lower()) else int(val)
        ports = {}
        for raw_entry in port_blk.split(","):
            entry = " ".join(raw_entry.strip().split())
            if not entry:
                continue
            pm = re.match(
                r"^(input|output)\s+(logic|real)\s*(?:\[\s*([^:\]]+)\s*:\s*(\d+)\s*\]\s*)?(\w+)$",
                entry,
            )
            assert pm, f"unparsed port declaration in {name}: {entry!r}"
            direction, ptype, msb, lsb, pname = pm.groups()
            if ptype == "real":
                width = "real"
            elif msb is None:
                width = 1
            else:
                msb_expr = msb.strip()
                for k, v in params.items():
                    msb_expr = re.sub(rf"\b{k}\b", str(v), msb_expr)
                hi = int(eval(msb_expr, {"__builtins__": {}}, {}))
                lo = int(lsb)
                width = hi - lo + 1
            ports[pname] = (direction, width)
        modules[name] = {"params": params, "ports": ports, "body": body}
    return modules


def parse_instance_connections(body, module_name, inst_name):
    pat = re.compile(rf"\b{module_name}\b\s*(?:#\s*\(.*?\)\s*)?\b{inst_name}\s*\((.*?)\)\s*;", re.S)
    m = pat.search(body)
    assert m, f"missing instance {module_name} {inst_name}"
    conns = {}
    for cm in re.finditer(r"\.(\w+)\s*\(\s*([^)]*)\s*\)", m.group(1)):
        conns[cm.group(1)] = cm.group(2).strip()
    return conns


def sar_quantize_rn(v_sensor, a0_lin, v_opamp_os=0.0, v_comp_os=0.0, vdd_ana=1.206):
    vcm, vref_lo, vref_hi = 0.600, 0.200, 1.000
    cl_gain = 1.0 / (1.0 + 2.0 / a0_lin)
    v_raw = vcm - (v_sensor - vcm) * cl_gain + 2.0 * v_opamp_os
    v_hi = 1.031 if vdd_ana >= 1.160 else max(0.06189, vdd_ana - 0.1294)
    v_held = max(0.06189, min(v_hi, v_raw))
    dac = 0
    for bit in range(7, -1, -1):
        trial = dac | (1 << bit)
        v_dac = vref_lo + (trial / 256.0) * (vref_hi - vref_lo)
        v_top = vcm + (v_dac - v_held)
        if (vcm + v_comp_os) > v_top:
            dac = trial
    return dac, v_held


def test_port_matching_across_rtl_models_wrapper_and_cocotb():
    assert RN_SV.exists(), f"missing {RN_SV}"
    assert COSIM_SV.exists(), f"missing {COSIM_SV}"
    assert COCOTB_PY.exists(), f"missing {COCOTB_PY}"

    rn_mods = parse_sv_modules(RN_SV.read_text(encoding="utf-8"))
    for req in ("rn_bandgap_ldo", "rn_opamp_adc", "rn_dldo_rail"):
        assert req in rn_mods, f"{req} missing from rn_analog_models.sv"

    cosim_mods = parse_sv_modules(COSIM_SV.read_text(encoding="utf-8"))
    assert "whole_chip_cosim_top" in cosim_mods
    cosim = cosim_mods["whole_chip_cosim_top"]

    if TOP_SV.exists():
        top_mods = parse_sv_modules(TOP_SV.read_text(encoding="utf-8"))
        assert "whole_chip_top" in top_mods
        chip_ports = top_mods["whole_chip_top"]["ports"]
        assert chip_ports == EXPECTED_WHOLE_CHIP_TOP_PORTS
    else:
        chip_ports = EXPECTED_WHOLE_CHIP_TOP_PORTS

    u_chip = parse_instance_connections(cosim["body"], "whole_chip_top", "u_chip")
    assert set(u_chip.keys()) == set(chip_ports.keys())

    u_bg = parse_instance_connections(cosim["body"], "rn_bandgap_ldo", "u_bg_ldo")
    assert set(u_bg.keys()) == set(rn_mods["rn_bandgap_ldo"]["ports"].keys())

    u_adc = parse_instance_connections(cosim["body"], "rn_opamp_adc", "u_opamp_adc")
    assert set(u_adc.keys()) == set(rn_mods["rn_opamp_adc"]["ports"].keys())
    for sig in ("adc_samp", "adc_comp_clk", "adc_dac", "comp_out"):
        assert u_adc[sig] == u_chip[sig], f"mismatched ADC net for {sig}"

    u_dldo = parse_instance_connections(cosim["body"], "rn_dldo_rail", "u_dldo_rail")
    assert set(u_dldo.keys()) == set(rn_mods["rn_dldo_rail"]["ports"].keys())
    assert u_dldo["lo"] == u_chip["dldo_lo"]
    assert u_dldo["hi"] == u_chip["dldo_hi"]
    assert u_dldo["far_lo"] == u_chip["dldo_far_lo"]
    assert u_dldo["far_hi"] == u_chip["dldo_far_hi"]
    assert u_dldo["droop_alert"] == u_chip["droop_alert"]
    assert u_dldo["dldo_on"] == u_chip["dldo_on"]
    assert u_dldo["dvfs_state"] == u_chip["dvfs_state"]
    assert u_dldo["cpu_sleep"] == u_chip["cpu_sleep"]
    assert rn_mods["rn_dldo_rail"]["ports"]["dldo_on"] == ("input", 128)
    assert rn_mods["rn_opamp_adc"]["ports"]["adc_dac"] == ("input", 8)

    tree = ast.parse(COCOTB_PY.read_text(encoding="utf-8"))
    dut_attrs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "dut":
            if not node.attr.startswith("_"):
                dut_attrs.add(node.attr)
    allowed = set(cosim["ports"].keys()) | {"u_chip", "u_bg_ldo", "u_opamp_adc", "u_dldo_rail"}
    unknown = dut_attrs - allowed
    assert not unknown, f"test_whole_chip_cocotb.py references unknown dut attributes: {sorted(unknown)}"
    for required_port in ("vin_3v3_uv", "v_sensor_uv", "i_analog_ua", "i_load_step_ua", "vdd_ana_uv", "vdd_cpu_uv", "por_ok", "droop_alert", "dvfs_state", "fir_last", "peak_last", "adc_overflow"):
        assert required_port in dut_attrs, f"cocotb testbench never accesses {required_port}"


def test_opamp_dc_gain_and_headroom_within_chip_md_limits():
    rn_mods = parse_sv_modules(RN_SV.read_text(encoding="utf-8"))
    p = rn_mods["rn_opamp_adc"]["params"]
    a0_typ = p["A0_LIN"]
    assert 20.0 * math.log10(a0_typ) >= 66.0
    static_err_typ_v = 0.4 * (2.0 / a0_typ)
    assert static_err_typ_v <= 0.00078

    corners_text = OPAMP_CORNERS.read_text(encoding="utf-8")
    m_a0 = re.search(r"a0_db\s+worst\s+([0-9.]+)", corners_text)
    assert m_a0, "missing worst a0_db in opamp corners.log"
    a0_worst_db = float(m_a0.group(1))
    a0_worst_lin = 10.0 ** (a0_worst_db / 20.0)
    assert a0_worst_db >= 66.0
    assert 0.4 * (2.0 / a0_worst_lin) <= 0.00078

    mc_text = OPAMP_MC.read_text(encoding="utf-8")
    m_off = re.search(r"offset_v\s+mean\s+[0-9.eE+-]+\s+sigma\s+([0-9.eE+-]+)\s+worst\s+([0-9.eE+-]+)", mc_text)
    assert m_off, "missing offset summary in opamp mc.log"
    worst_os_v = float(m_off.group(2))
    gain_err_worst = 1.0 - 1.0 / (1.0 + 2.0 / a0_worst_lin)
    peak_err_v = 2.0 * worst_os_v + gain_err_worst * 0.357
    assert peak_err_v <= 0.0376


def test_adc_real_number_quantizer_enob_matches_chip_md():
    rn_mods = parse_sv_modules(RN_SV.read_text(encoding="utf-8"))
    a0_lin = rn_mods["rn_opamp_adc"]["params"]["A0_LIN"]
    fs, n, k = 1e6, 1024, 31
    fin = k * fs / n
    assert coherent_bin(fs, n, fin) == k
    amp = 0.4 * (10.0 ** (-0.5 / 20.0))
    codes = [
        sar_quantize_rn(0.6 + amp * math.sin(2.0 * math.pi * fin * i / fs), a0_lin=a0_lin)[0]
        for i in range(n)
    ]
    res = spectrum(codes, k)
    assert 7.9 <= res["enob"] <= 8.1, f"ENOB {res['enob']:.3f} outside 8.0 +- 0.1"
    assert abs(res["tone_dbfs"] - (-0.5)) < 0.05
    assert min(codes) > 0 and max(codes) < 255


def test_dldo_window_thresholds_and_dvfs_speed_log_consistency():
    rn_mods = parse_sv_modules(RN_SV.read_text(encoding="utf-8"))
    bg_p = rn_mods["rn_bandgap_ldo"]["params"]
    dl_p = rn_mods["rn_dldo_rail"]["params"]
    vref = bg_p["VREF_NOM_V"]
    assert abs(vref - 1.206) < 1e-6
    expected_taps = {
        "V_TAP_FAR_LO": 0.570,
        "V_TAP_LO": 0.594,
        "V_TAP_HI": 0.606,
        "V_TAP_FAR_HI": 0.630,
    }
    for name, want_v in expected_taps.items():
        assert abs(dl_p[name] - want_v) < 1e-6, f"{name}={dl_p[name]}, expected {want_v}"
    for tap_idx, want_v in ((95, 0.570), (99, 0.594), (101, 0.606), (105, 0.630)):
        assert abs(vref * (tap_idx / 201.0) - want_v) < 1e-4

    assert dl_p["N_UNITS"] == 128
    assert abs(dl_p["C_RAIL_F"] - 2.0e-9) < 1e-12
    assert dl_p["N_UNITS"] * 115e-6 >= 12.0e-3

    speed_text = SPEED_LOG.read_text(encoding="utf-8")
    factors = {
        round(float(m.group(1)), 2): float(m.group(2))
        for m in re.finditer(r"vdd\s+([0-9.]+)\s+V:\s+worst\s+slow-corner\s+delay\s+([0-9.]+)\s+x", speed_text)
    }
    for v_target in (0.90, 1.00, 1.10, 1.20):
        assert v_target in factors
        v_fb_nom = v_target * (0.600 / v_target)
        assert dl_p["V_TAP_LO"] < v_fb_nom < dl_p["V_TAP_HI"]
        assert (0.94 * v_target) * (0.600 / v_target) < dl_p["V_TAP_FAR_LO"]
        assert (1.06 * v_target) * (0.600 / v_target) > dl_p["V_TAP_FAR_HI"]
    assert factors[0.90] > factors[1.00] > factors[1.10] > factors[1.20]


def test_bandgap_ldo_regulation_and_droop_floor_limits():
    rn_mods = parse_sv_modules(RN_SV.read_text(encoding="utf-8"))
    p = rn_mods["rn_bandgap_ldo"]["params"]
    assert p["VDD_MIN_OK_V"] >= 1.160
    assert p["VDD_MAX_OX_V"] <= 1.320
    assert p["R_LOAD_REG"] * 2.0e-3 <= 5.0e-3
    assert p["LINE_REG_VPV"] <= 10.0e-3
    v_step_min = p["VREF_NOM_V"] - p["R_LOAD_REG"] * 0.5e-3 - p["R_TRANS_OHM"] * 0.5e-3
    assert v_step_min >= 1.160, f"0.5 mA load step floor {v_step_min:.4f} V drops below 1.16 V"
    v_release_max = p["VREF_NOM_V"] + p["R_TRANS_OHM"] * 2.0e-3
    assert v_release_max <= 1.320, f"2 mA release peak {v_release_max:.4f} V exceeds 1.32 V thin-oxide limit"


def test_droop_por_bod_model():
    rn_mods = parse_sv_modules(RN_SV.read_text(encoding="utf-8"))
    bg_p = rn_mods["rn_bandgap_ldo"]["params"]
    dl_p = rn_mods["rn_dldo_rail"]["params"]

    por_rise_mv = int(round(bg_p["VDD_MIN_OK_V"] * 1000))
    bod_trip_mv = 800
    bod_hyst_mv = 40
    assert por_rise_mv == 1160
    assert 900 - bod_trip_mv == 100

    por_cnt, por_n, bod_alert, droop_alert = 0, 0, 0, 1
    ramp_mv = [400, 800, 1100, 1165, 1180, 1200, 1205]
    for v_mv in ramp_mv:
        if v_mv >= por_rise_mv:
            por_cnt += 1
            if por_cnt >= 2:
                por_n = 1
        else:
            por_cnt = 0
        if v_mv < por_rise_mv:
            assert por_n == 0
    assert por_n == 1

    dvfs0_ripple_mv = 885
    assert dvfs0_ripple_mv >= bod_trip_mv
    assert dvfs0_ripple_mv < (bod_trip_mv + 100), "100 mV shifted BOD threshold must falsely trip at DVFS 0.90 V"

    droop_thresh_1v2_mv = int(round(1200 * (dl_p["V_TAP_FAR_LO"] / 0.600)))
    recover_thresh_1v2_mv = int(round(1200 * (dl_p["V_DROOP_REL"] / 0.600)))
    assert droop_thresh_1v2_mv == 1140
    assert recover_thresh_1v2_mv == 1170

    wave_mv = [1200, 1195, 1120, 1105, 1135, 1155, 1175, 1198, 780, 810, 1185]
    stretched_cycles = 0
    bod_trips = 0
    for v_mv in wave_mv:
        if v_mv < bod_trip_mv:
            bod_alert = 1
        elif v_mv >= bod_trip_mv + bod_hyst_mv:
            bod_alert = 0
        if bod_alert:
            bod_trips += 1
        if v_mv < droop_thresh_1v2_mv:
            droop_alert = 1
        elif v_mv >= recover_thresh_1v2_mv:
            droop_alert = 0
        clk_cpu_en = int(por_n == 1 and bod_alert == 0 and droop_alert == 0)
        if not clk_cpu_en and not bod_alert:
            stretched_cycles += 1
    assert stretched_cycles == 4
    assert bod_trips == 2
    assert bod_alert == 0

