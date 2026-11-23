# Plants every kind of cheat in a scratch folder, including results older than their sources and README numbers no log shows, and checks that check_honesty catches each one.
import json, subprocess
from check_honesty import find_problems
from save_result import save

def write(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path

def rules(root):
    return sorted({rule for rule, _, _ in find_problems(root)})

def test_clean_tree_passes(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    write(tmp_path, "design/amp.sp", "two stage amp\n.lib cornerMOSlv.lib mos_tt\nXM1 d g s b sg13_lv_nmos w=1u l=1u\n")
    write(tmp_path, "helpers/read.py", "# Reads a log.\nimport numpy as np\nprint(np.mean([1, 2]))\n")
    write(tmp_path, "design/top.sv", "// Top level.\nmodule top(input logic a, output logic y);\n  assign y = a;\nendmodule\n")
    write(tmp_path, "Makefile", "# Runs tests.\ntest:\n\tngspice -b amp.sp\n")
    log = write(tmp_path, "results/run.log", "ok")
    save(tmp_path / "results/summary.json", "sim", True, [log], root=tmp_path)
    assert find_problems(tmp_path) == []

def test_catches_each_cheat(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    write(tmp_path, "toy.sp", "toy\n.model nch nmos level=1 vto=0.4\n")
    write(tmp_path, "helpers/fallback.py", "# Fallback.\ntry:\n    open('x')\nexcept FileNotFoundError:\n    pass\n")
    write(tmp_path, "helpers/fake.py", "# Fake.\nimport numpy as np\ngain = 60 + np.random.normal(0, 1)\n")
    write(tmp_path, "helpers/sim.py", "# Sim.\nfrom scipy.integrate import solve_ivp\n")
    write(tmp_path, "Makefile", "# Hides failures.\ntest:\n\tngspice -b amp.sp || true\n")
    write(tmp_path, "chatty.sv", "// One.\n// Two.\nmodule m; endmodule\n")
    write(tmp_path, "silent.py", "x = 1\n")
    log = write(tmp_path, "results/run.log", "ok")
    save(tmp_path / "results/summary.json", "sim", True, [log], root=tmp_path)
    log.write_text("edited after the fact")
    summary = tmp_path / "results/summary.json"
    data = json.loads(summary.read_text())
    data["fake"] = {"result": "pass", "logs": {}, "values": {}, "time": "now"}
    summary.write_text(json.dumps(data))
    assert rules(tmp_path) == ["bad_log", "comments", "fake_fallback", "hidden_failure",
                               "made_up_numbers", "python_simulation", "stale_result", "toy_model"]

def test_spice_title_is_its_one_comment(tmp_path):
    write(tmp_path, "a.sp", "title line\n* extra comment\nR1 a 0 1k\n")
    assert rules(tmp_path) == ["comments"]

def test_result_goes_stale_when_a_source_or_used_helper_changes(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    design = write(tmp_path, "proj/design/top.sv", "// Top.\nmodule top; endmodule\n")
    write(tmp_path, "proj/tests/run.py", "# Runs.\nimport used\n")
    used = write(tmp_path, "helpers/used.py", "# Used.\nx = 1\n")
    log = write(tmp_path, "proj/results/run.log", "ok")
    save(tmp_path / "proj/results/summary.json", "sim", True, [log], root=tmp_path)
    write(tmp_path, "proj/README.md", "notes")
    write(tmp_path, "helpers/unrelated.py", "# Unrelated.\n")
    assert rules(tmp_path) == []
    design.write_text("// Top.\nmodule top(input a); endmodule\n")
    assert rules(tmp_path) == ["stale_result"]
    design.write_text("// Top.\nmodule top; endmodule\n")
    used.write_text("# Used.\nx = 2\n")
    assert rules(tmp_path) == ["stale_result"]

def test_readme_numbers_must_come_from_their_logs(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    write(tmp_path, "proj/results/synth.log", "Chip area for module fifo_bridge: 16726.95\n")
    readme = write(tmp_path, "proj/README.md", "| Check | Result | Where |\n|---|---|---|\n| Cells | area 16726.95 um2 | `results/synth.log` |\n")
    assert rules(tmp_path) == []
    readme.write_text(readme.read_text().replace("16726.95", "15613"))
    assert rules(tmp_path) == ["readme_claim"]
    readme.write_text(readme.read_text().replace("synth.log", "timing.log"))
    assert rules(tmp_path) == ["readme_claim"]

def test_readme_numbers_must_match_whole_log_numbers(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    write(tmp_path, "proj/results/a.log", "Chip area 16708.809600\nworst setup slack 14.959187666363505 ns, hold 0.12318109032793956 ns\nTotal 1.89e-04 W\nworst bridge MTBF 10^51 years\ntau 133.8 ps\n")
    good = "| Check | Area | Slack | Power | MTBF | Tau | Where |\n|---|---|---|---|---|---|---|\n| x | area 16708.8 um2 | setup slack 14.96 ns | Total 1.89e-04 W | MTBF 10^51 years | tau 133.8 ps | `results/a.log` |\n"
    readme = write(tmp_path, "proj/README.md", good)
    assert rules(tmp_path) == []
    for right, wrong in [("16708.8", "1670"), ("14.96", "14.9"), ("1.89e-04", "1.8e-04"), ("10^51", "10^5"), ("133.8", "13.8"), ("14.96", "0.12")]:
        readme.write_text(good.replace(right, wrong))
        assert rules(tmp_path) == ["readme_claim"], wrong
    readme.write_text(good + "| y | 3.2 | 1 | 2 | 3 | 4 | none |\n")
    assert rules(tmp_path) == ["readme_claim"]

def test_readme_numbers_must_sit_on_a_log_line_with_their_label(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    write(tmp_path, "proj/results/synth.log", "   Number of cells:               1015\n     sg13g2_dfrbpq_1 flops          208\n   10 20 1 spare numbers\n")
    write(tmp_path, "proj/results/pause.log", "longest pause with no lost sample: 17 us\n")
    write(tmp_path, "proj/results/mtbf.log", "ss rise: tau 133.8 ps\n")
    good = ("| Check | Result | Where |\n|---|---|---|\n| Cells | 1015 cells, 208 flops | `results/synth.log` |\n| Pause | longest pause 17 us | `results/pause.log` |\n\n"
            "| Corner | Tau | Where |\n|---|---|---|\n| ss, rise | tau 133.8 ps | `results/mtbf.log` |\n\n| Item | Value |\n|---|---|\n| Clock | 10 MHz |\n")
    readme = write(tmp_path, "proj/README.md", good)
    assert rules(tmp_path) == []
    for right, wrong in [("1015 cells, 208 flops", "10 cells, 20 flops"), ("pause 17 us", "pause 1 us"), ("133.8", "13.8")]:
        readme.write_text(good.replace(right, wrong))
        assert rules(tmp_path) == ["readme_claim"], wrong
    readme.write_text(good + "\n| Corner | Tau |\n|---|---|\n| tt | 71.1 ps |\n")
    assert rules(tmp_path) == ["readme_claim"]

def test_a_makefile_branch_that_drops_an_exit_code_is_a_hidden_failure(tmp_path):
    write(tmp_path, "Makefile", "# Runs the flow.\nall:\n\tif ./flow > out.log; then c=0; else c=$$?; fi\n")
    assert rules(tmp_path) == []
    write(tmp_path, "Makefile", "# Runs the flow.\nall:\n\tif ./flow > out.log; then :; else tail out.log; fi\n")
    assert rules(tmp_path) == ["hidden_failure"]

def test_a_hand_written_rail_integrator_is_a_python_simulation(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    write(tmp_path, "tests/test_rail.py", "# Rail.\nv = 0.0\nfor _ in range(10):\n    v = max(0.0, v + (drive * unit_a - load_a * v / vset) * period_s / cap_f)\n")
    assert rules(tmp_path) == ["python_simulation"]
    write(tmp_path, "tests/test_rail.py", "# Arithmetic.\ngain = 1000 * 10 / 10.1\nfor k in range(3):\n    tau = k * cap_f / g\n")
    assert rules(tmp_path) == []

def test_a_uses_entry_that_does_not_exist_is_reported_not_a_crash(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    write(tmp_path, "proj/design/top.sv", "// Top level.\nmodule top(input logic a, output logic y);\n  assign y = a;\nendmodule\n")
    log = write(tmp_path, "proj/results/run.log", "ok")
    save(tmp_path / "proj/results/summary.json", "sim", True, [log], root=tmp_path)
    write(tmp_path, "proj/uses.txt", "other/results/gone.log\n")
    found = find_problems(tmp_path)
    assert ("missing_use", "other/results/gone.log") in {(rule, why.split()[-1]) for rule, _, why in found}

def test_a_value_preset_before_it_is_measured_is_a_silent_default(tmp_path):
    write(tmp_path, "tests/load.cir", "load bench\n.control\nlet error = 0\nmeas tran got find v(out) at=1u\nlet error = abs(got - 1)\nquit\n.endc\n")
    write(tmp_path, "tests/dc.cir", "dc bench\n.control\nlet tc = 0\nmeas dc tc find v(out) at=27\nquit\n.endc\n")
    write(tmp_path, "tests/step.cir", "step bench\n.control\nlet ub = -1\nmeas tran ub when v(out)=1 cross=last\necho \"may be absent: ub (the output never overshoots)\"\nquit\n.endc\n")
    write(tmp_path, "tests/ok.cir", "ok bench\n.control\nlet span = 0.6\nmeas tran got find v(out) at=1u\nquit\n.endc\n")
    found = {(rule, str(path)) for rule, path, _ in find_problems(tmp_path)}
    assert ("silent_default", "tests/load.cir") in found and ("silent_default", "tests/dc.cir") in found
    assert not any(path in ("tests/step.cir", "tests/ok.cir") for rule, path in found if rule == "silent_default")
