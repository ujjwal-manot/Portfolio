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
    readme = write(tmp_path, "proj/README.md", "| Check | Result | Where |\n|---|---|---|\n| Cells | 16726.95 um2 | `results/synth.log` |\n")
    assert rules(tmp_path) == []
    readme.write_text(readme.read_text().replace("16726.95", "15613"))
    assert rules(tmp_path) == ["readme_claim"]
    readme.write_text(readme.read_text().replace("synth.log", "timing.log"))
    assert rules(tmp_path) == ["readme_claim"]
