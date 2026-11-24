# Plants every kind of cheat in a scratch folder, including results older than their sources and README numbers no log shows, and checks that check_honesty catches each one.
import json, subprocess
from pathlib import Path
from check_honesty import find_problems, exact_zeros, ignores_errors
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
    write(tmp_path, "Makefile", "# Runs tests.\ntest:\n\thelpers/ngspice.sh amp.sp amp.log\n")
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
                               "made_up_numbers", "python_simulation", "stale_result", "toy_model", "unchecked_log"]

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
    write(tmp_path, "tests/loop.cir", "loop bench\n.control\nlet k = 0\nwhile k < 4\nlet k = k + 1\nend\nquit\n.endc\n")
    write(tmp_path, "tests/clamp.cir", "clamp bench\n.control\nlet code = 1e400 - 1e400\nmeas tran v8 find v(out) at=1u\nlet code = floor(v8 * 10)\nif code < 0\nlet code = 0\nend\nquit\n.endc\n")
    write(tmp_path, "tests/search.cir", "search bench\n.control\nlet lo = -0.02\nlet hi = 0.02\nlet mid = (lo + hi) / 2\nlet hi = mid\nquit\n.endc\n")
    write(tmp_path, "tests/tend.cir", "tend bench\n.control\nlet tend = 0\ntran 1n 1u\nlet tend = time[length(time) - 1]\nquit\n.endc\n")
    write(tmp_path, "tests/sum.cir", "sum bench\n.control\nlet total = 0\nmeas tran v1 find v(out) at=1u\nlet total = total + v1\nquit\n.endc\n")
    found = {(rule, str(path)) for rule, path, _ in find_problems(tmp_path)}
    assert ("silent_default", "tests/load.cir") in found and ("silent_default", "tests/dc.cir") in found
    assert ("silent_default", "tests/sum.cir") in found and ("silent_default", "tests/tend.cir") in found
    assert not any(path in ("tests/step.cir", "tests/ok.cir", "tests/loop.cir", "tests/clamp.cir", "tests/search.cir") for rule, path in found if rule == "silent_default")

def test_a_preset_cannot_dodge_the_rule_by_its_spelling_or_a_chain(tmp_path):
    for name, preset in [("sum", "0+0"), ("paren", "(0)"), ("vec", "vector(1)")]:
        write(tmp_path, f"tests/{name}.cir", f"{name} bench\n.control\nlet x = {preset}\nmeas tran x find v(out) at=1u\nquit\n.endc\n")
    write(tmp_path, "tests/chain.cir", "chain bench\n.control\nlet t = 0\nmeas tran a find v(out) at=1u\nlet b = a * 2\nlet t = b\nquit\n.endc\n")
    write(tmp_path, "tests/nan.cir", "nan bench\n.control\nlet nan = 1e400 - 1e400\nlet x = nan\nmeas tran x find v(out) at=1u\nquit\n.endc\n")
    found = {str(path) for rule, path, _ in find_problems(tmp_path) if rule == "silent_default"}
    assert {"tests/sum.cir", "tests/paren.cir", "tests/vec.cir", "tests/chain.cir"} <= found and "tests/nan.cir" not in found

def test_a_meas_in_a_loop_must_be_reset_each_pass(tmp_path):
    write(tmp_path, "tests/stale.cir", "stale bench\n.control\nlet k = 0\nwhile k < 4\ntran 1n 1u\nmeas tran level find v(out) at=1u\nlet k = k + 1\nend\nquit\n.endc\n")
    write(tmp_path, "tests/reset.cir", "reset bench\n.control\nlet nan = 1e400 - 1e400\nlet k = 0\nwhile k < 4\nlet level = nan\ntran 1n 1u\nmeas tran level find v(out) at=1u\nlet k = k + 1\nend\nquit\n.endc\n")
    write(tmp_path, "tests/destroy.cir", "destroy bench\n.control\nforeach c 1 2\ndestroy all\ntran 1n 1u\nmeas tran level find v(out) at=1u\nend\nquit\n.endc\n")
    found = {str(path) for rule, path, _ in find_problems(tmp_path) if rule == "stale_meas"}
    assert found == {"tests/stale.cir"}

def test_the_loop_and_preset_rules_cannot_be_dodged(tmp_path):
    nan = "let nan = 1e400 - 1e400\n"
    write(tmp_path, "tests/spelled.cir", "spelled\n.control\nlet w = 5\nmeasure tran w find v(a) at=1u\nquit\n.endc\n")
    write(tmp_path, "tests/ifblock.cir", "ifblock\n.control\nlet k = 0\nwhile k < 3\nif k > 1\nlet k = k\nend\ntran 1n 1u\nmeas tran q find v(a) at=1u\nlet k = k + 1\nend\nquit\n.endc\n")
    write(tmp_path, "tests/outer.cir", "outer\n.control\n" + nan + "let j = 0\nwhile j < 2\nlet q = nan\nlet k = 0\nwhile k < 2\ntran 1n 1u\nmeas tran q find v(a) at=1u\nlet k = k + 1\nend\nlet j = j + 1\nend\nquit\n.endc\n")
    write(tmp_path, "tests/zero.cir", "zero\n.control\nlet x = 1e100 - 1e100\nmeas tran x find v(a) at=1u\nquit\n.endc\n")
    write(tmp_path, "tests/late.cir", "late\n.control\ntran 1n 1u\n" + nan + "let k = 0\nwhile k < 2\nlet q = nan\nmeas tran q find v(a) at=1u\nlet k = k + 1\nend\nquit\n.endc\n")
    write(tmp_path, "tests/good.cir", "good\n.control\n" + nan + "let k = 0\nwhile k < 2\nif k > 0\nlet k = k\nend\nlet q = nan\ntran 1n 1u\nmeas tran q find v(a) at=1u\nlet k = k + 1\nend\nquit\n.endc\n")
    found = {(rule, str(path)) for rule, path, _ in find_problems(tmp_path) if rule in ("silent_default", "stale_meas")}
    for name in ("spelled", "ifblock", "outer", "zero", "late"):
        assert any(path == f"tests/{name}.cir" for _, path in found), name
    assert not any(path == "tests/good.cir" for _, path in found)

def test_every_ngspice_run_in_a_makefile_goes_through_the_checked_wrapper(tmp_path):
    bad = {
        "direct": "\tcd build && $(RUN) ngspice -b dc.cir > dc.log 2>&1\n\t$(PY) helpers/spice_log_check.py build/dc.log\n",
        "batch": "\tcd build && $(RUN) ngspice --batch dc.cir > dc.log 2>&1\n",
        "ignored": "\tcd build && $(RUN) ngspice -b x.cir > x.log 2>&1; $(L) x.log; exit 0\n",
        "tworule": "\t$(SPICE) a.cir a.log\nother:\n\tcd build && $(RUN) ngspice -b b.cir > b.log 2>&1\n",
        "loop": "\tfor t in a b; do $(SPICE) $$t.cir $$t.log; done\n",
        "subshell": "\t(cd d && $(SPICE) a.cir a.log); cp d/a.txt results/\n",
        "true": "\t$(SPICE) a.cir a.log || true\n",
        "zero": "\t$(SPICE) a.cir a.log || c=0\n",
        "echoed": "\t$(SPICE) a.cir a.log && echo fine || echo bad\n",
        "noelse": "\tif $(SPICE) a.cir a.log; then echo ok; fi\n",
        "unread": "\tif ! $(SPICE) a.cir a.log; then echo \"a failed\" >> failed.txt; fi\n",
        "echofile": "\tif ! $(SPICE) a.cir a.log; then echo \"a failed\" >> notes.txt; fi\n",
        "noop": "\tif ! $(SPICE) a.cir a.log; then :; fi\n",
        "dash": "\t-$(SPICE) a.cir a.log\n",
        "atdash": "\t@-$(SPICE) a.cir a.log\n",
        "ignore": "\t$(SPICE) a.cir a.log\n.IGNORE:\n",
        "keepgoing": "\t$(SPICE) a.cir a.log\nMAKEFLAGS += -k\n",
    }
    good = {
        "plain": "\tcd build && $(SPICE) dc.cir dc.log\n",
        "chained": "\tcd build && $(SPICE) dc.cir dc.log && cp dc.txt ../results/\n",
        "recorded": "\tfor t in a b; do $(SPICE) $$t.cir $$t.log || c=1; done; exit $$c\n",
        "iftest": "\tif ! (cd d && $(SPICE) a.cir a.log); then c=1; fi\n",
        "failfile": "\tif ! $(SPICE) a.cir a.log; then echo \"a failed\" >> failed.txt; fi\n\ttest ! -s failed.txt\n",
        "elsebranch": "\tif $(SPICE) a.cir a.log; then echo ok; else exit 1; fi\n",
        "continued": "\tif ! $(SPICE) a.cir a.log; then \\\n\t  c=1; fi\n",
        "direct_path": "\tcd build && $(ROOT)/helpers/ngspice.sh dc.cir dc.log\n",
        "codegen": "\tcd build && $(RUN) ngspice vlnggen top.sv > vlnggen.log 2>&1\n",
    }
    for name, recipe in {**bad, **good}.items():
        write(tmp_path, f"{name}/Makefile", "# Runs a bench.\nSPICE := $(ROOT)/helpers/ngspice.sh\nrun:\n" + recipe)
    found = {str(path).split("/")[0] for rule, path, _ in find_problems(tmp_path) if rule in ("unchecked_log", "hidden_failure")}
    assert found == set(bad)

def test_the_wrapper_fails_when_the_log_check_fails(tmp_path):
    fake = write(tmp_path, "setup/run.sh", "#!/bin/bash\n# Fake tool runner.\nif [ \"$1\" = ngspice ]; then cat " + str(Path(__file__).parent / "fixtures/spice_logs") + "/$3; else exec \"$@\"; fi\n")
    fake.chmod(0o755)
    wrapper = tmp_path / "helpers/ngspice.sh"
    wrapper.parent.mkdir()
    wrapper.write_text((Path(__file__).parent / "ngspice.sh").read_text())
    wrapper.chmod(0o755)
    (tmp_path / "helpers/spice_log_check.py").write_text((Path(__file__).parent / "spice_log_check.py").read_text())
    good = subprocess.run([str(wrapper), "clean.log", str(tmp_path / "a.log")], capture_output=True, text=True)
    bad = subprocess.run([str(wrapper), "killed.log", str(tmp_path / "b.log")], capture_output=True, text=True)
    assert good.returncode == 0 and bad.returncode != 0
    assert "ngspice-47 done" in (tmp_path / "a.log").read_text()

def test_an_exact_zero_in_a_result_is_flagged_unless_the_bench_says_why(tmp_path):
    write(tmp_path, "p/results/pairs.txt", "load settle_load_v 0 kick_v 1.2e-3\n")
    write(tmp_path, "p/results/table.txt", "dv_v t_decide_s\n10e-3 0.0\n")
    write(tmp_path, "p/results/negative.txt", "load err_v -0.0e+00\n")
    write(tmp_path, "p/results/real.txt", "bias vsb 0 id_a 1e-5\nzero is real: vsb (the source is tied to the bulk)\n")
    write(tmp_path, "p/results/noreason.txt", "bias vsb 0\nzero is real: vsb\n")
    write(tmp_path, "p/results/small.txt", "load settle_load_v 1e-300 code 10\n")
    found = {str(path).split("/")[-1] for rule, path, _ in find_problems(tmp_path) if rule == "exact_zero"}
    assert found == {"pairs.txt", "table.txt", "negative.txt", "noreason.txt"}

def test_every_way_make_can_ignore_an_error_is_a_hidden_failure(tmp_path):
    bad = {
        "spaced": "a:\n\t @ - false\n", "dashspace": "a:\n\t- false\n", "plus": "a:\n\t+-false\n",
        "sameline": "b: ; -false\n", "long": "MAKEFLAGS += --ignore-errors\na:\n\tfalse\n",
        "keep": "MAKEFLAGS += --keep-going\na:\n\tfalse\n", "letter": "MAKEFLAGS += i\na:\n\tfalse\n",
        "colon": "a:\n\t$(PY) check.py x.log || :\n",
    }
    good = {"plain": "a:\n\t@echo -n x\n", "flags": "MAKEFLAGS += --no-print-directory\na:\n\tfalse\n", "rule": "a: b ; @echo -x\n"}
    for name, body in {**bad, **good}.items():
        write(tmp_path, f"{name}/Makefile", "# Runs a bench.\n" + body)
    found = {str(path).split("/")[0] for rule, path, _ in find_problems(tmp_path) if rule == "hidden_failure"}
    assert found == set(bad)

def test_exact_zero_reads_every_row_and_each_separator(tmp_path):
    for name, text in {"third": "code err\n5 0.1\n6 0.2\n7 0\n", "equals": "settle_v=0 kick_v=1e-3\n", "colon": "settle_v: 0\n",
                       "csv": "code,err\n5,0.1\n6,0\n", "pair": "settle_v,0\n"}.items():
        assert exact_zeros(text), name
    assert exact_zeros("code err\n5 0.1\n6 0.2\n") == []
    assert exact_zeros("temp_c vbe_v\n-40 0.8\n0 0.7\nzero is real: temp_c (a sweep point)\n") == []

def test_makeflags_with_a_prefix_or_an_option_argument(tmp_path):
    assert ignores_errors("export MAKEFLAGS += i") and ignores_errors("override MAKEFLAGS += -i")
    assert not ignores_errors("MAKEFLAGS += -I include") and not ignores_errors("MAKEFLAGS += -C dir -W file")
