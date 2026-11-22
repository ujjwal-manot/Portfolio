# Verifies projects/power_manager/design/droop_por_bod.sv and dldo_ctrl.sv ports/parameters against speed.log and checks that all three plan.md broken/*.patch files apply cleanly with git apply --check and break their target invariant.
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PM = HERE.parent
DLDO_SV = PM / "design" / "dldo_ctrl.sv"
DROOP_SV = PM / "design" / "droop_por_bod.sv"
BROKEN_DIR = PM / "broken"
SPEED_LOG = PM / "results" / "speed.log"


def parse_params_and_ports(sv_path):
    clean = re.sub(r"//.*", "", sv_path.read_text(encoding="utf-8"))
    m = re.search(r"\bmodule\s+(\w+)\s*(?:#\s*\((.*?)\)\s*)?\((.*?)\)\s*;(.*?)\bendmodule\b", clean, re.S)
    assert m, f"no module found in {sv_path}"
    params = {
        pm.group(1): int(pm.group(2))
        for pm in re.finditer(r"parameter\s+int\s+(\w+)\s*=\s*(\d+)", m.group(2) or "")
    }
    ports = {}
    for entry in m.group(3).split(","):
        s = " ".join(entry.strip().split())
        if not s:
            continue
        pm = re.match(r"^(input|output)\s+logic\s*(?:\[([^\]]+)\]\s*)?(\w+)$", s)
        assert pm, f"unparsed port {s!r} in {sv_path.name}"
        ports[pm.group(3)] = pm.group(1)
    return m.group(1), params, ports, m.group(4)


def apply_patch_in_memory(sv_text, patch_text):
    lines = sv_text.splitlines()
    for m in re.finditer(r"^@@ -(\d+),(\d+) \+(\d+),(\d+) @@\n((?:[ +-].*(?:\n|$))+)", patch_text, re.M):
        hunk_body = m.group(5).splitlines()
        old_block = [l[1:] for l in hunk_body if l.startswith((" ", "-"))]
        new_block = [l[1:] for l in hunk_body if l.startswith((" ", "+"))]
        found = False
        for i in range(len(lines) - len(old_block) + 1):
            if lines[i : i + len(old_block)] == old_block:
                lines = lines[:i] + new_block + lines[i + len(old_block) :]
                found = True
                break
        assert found, "patch hunk did not match target text"
    return "\n".join(lines) + "\n"


def eval_droop_por_bod(sv_text):
    clean = re.sub(r"//.*", "", sv_text)
    params = {
        pm.group(1): int(pm.group(2))
        for pm in re.finditer(r"parameter\s+int\s+(\w+)\s*=\s*(\d+)", clean)
    }
    stretch_enabled = "clk_cpu_en = sys_rst_n && !droop_alert" in clean
    return params, stretch_enabled


def eval_dldo_fine_step(sv_text):
    clean = re.sub(r"//.*", "", sv_text)
    m = re.search(r"else if \(up\)\s+next_count\s*=\s*next_count\s*\+\s*(\w+)", clean)
    assert m, "missing fine up step in dldo_ctrl.sv"
    tok = m.group(1)
    if tok.isdigit():
        return int(tok)
    pm = re.search(rf"parameter\s+int\s+{re.escape(tok)}\s*=\s*(\d+)", clean)
    assert pm
    return int(pm.group(1))


def test_droop_por_bod_ports_and_speed_log_calibration():
    assert DROOP_SV.exists(), f"missing {DROOP_SV}"
    mod_name, params, ports, body = parse_params_and_ports(DROOP_SV)
    assert mod_name == "droop_por_bod"
    expected_ports = {
        "clk_sys": "input",
        "rst_ext_n": "input",
        "bg_ok": "input",
        "dvfs_state": "input",
        "vdd_cpu_mv": "input",
        "delay_taps_reached": "input",
        "por_n": "output",
        "bod_alert": "output",
        "droop_alert": "output",
        "clk_cpu_en": "output",
        "clk_cpu": "output",
        "sys_rst_n": "output",
    }
    assert ports == expected_ports
    assert params["POR_RISE_MV"] == 1160
    assert params["BOD_TRIP_MV"] == 800
    assert params["DELAY_TAPS"] == 16
    assert "clk_cpu_en = sys_rst_n && !droop_alert" in body

    speed_text = SPEED_LOG.read_text(encoding="utf-8")
    factors = {
        round(float(m.group(1)), 2): float(m.group(2))
        for m in re.finditer(r"vdd\s+([0-9.]+)\s+V:\s+worst\s+slow-corner\s+delay\s+([0-9.]+)\s+x", speed_text)
    }
    assert factors[0.80] > 3.4 and factors[0.90] > 1.9 and factors[1.20] < 0.85


def test_all_three_power_manager_broken_patches_apply_and_catch_bugs():
    patches = [
        "controller_gain_too_high.patch",
        "clock_stretch_disabled.patch",
        "bod_threshold_off_100mv.patch",
    ]
    for pname in patches:
        ppath = BROKEN_DIR / pname
        assert ppath.exists(), f"missing broken patch {ppath}"
        first_line = ppath.read_text(encoding="utf-8").splitlines()[0]
        assert first_line.startswith("Expected failure: AssertionError:")
        res = subprocess.run(
            ["git", "apply", "--check", f"broken/{pname}"],
            cwd=PM,
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0, f"git apply --check failed for {pname}: {res.stderr}"

    dldo_orig = DLDO_SV.read_text(encoding="utf-8")
    droop_orig = DROOP_SV.read_text(encoding="utf-8")
    assert eval_dldo_fine_step(dldo_orig) == 1
    orig_params, orig_stretch = eval_droop_por_bod(droop_orig)
    assert orig_stretch is True
    assert orig_params["BOD_TRIP_MV"] == 800
    assert 885 >= orig_params["BOD_TRIP_MV"]

    dldo_high_gain = apply_patch_in_memory(dldo_orig, (BROKEN_DIR / "controller_gain_too_high.patch").read_text(encoding="utf-8"))
    assert eval_dldo_fine_step(dldo_high_gain) >= 16

    droop_no_stretch = apply_patch_in_memory(droop_orig, (BROKEN_DIR / "clock_stretch_disabled.patch").read_text(encoding="utf-8"))
    _, broken_stretch = eval_droop_por_bod(droop_no_stretch)
    assert broken_stretch is False

    droop_bad_bod = apply_patch_in_memory(droop_orig, (BROKEN_DIR / "bod_threshold_off_100mv.patch").read_text(encoding="utf-8"))
    bad_bod_params, _ = eval_droop_por_bod(droop_bad_bod)
    assert abs(bad_bod_params["BOD_TRIP_MV"] - orig_params["BOD_TRIP_MV"]) == 100
    assert 885 < bad_bod_params["BOD_TRIP_MV"]
