# Checks spice_log_check on real ngspice logs kept in fixtures/spice_logs: runs that finished (cleanly, with a stderr Note printed after ngspice's done line, after a failed dynamic gmin step, after a singular-matrix warning that gmin stepping cleared, after source stepping failed and the transient op took over, or with "failed" only in the bench's own title) pass; an operating point that never converged, a transient that stopped with a failed meas, a missing include file, a failed meas whose stderr lines landed after the done line, a run killed partway (no closing done line) and a meas that failed without being declared absent each fail with the line that shows why; the same step log passes once it carries the declaration a bench echoes for a measure that may be absent.
import subprocess, sys
from pathlib import Path
import pytest
from spice_log_check import problems

LOGS = Path(__file__).parent / "fixtures" / "spice_logs"

@pytest.mark.parametrize("name", ["clean.log", "converged_after_gmin_failed.log", "converged_after_singular_matrix.log",
                                  "converged_by_transient_op.log", "title_mentions_failure.log", "note_after_done.log"])
def test_a_run_that_finished_passes(name):
    assert problems((LOGS / name).read_text()) == []

@pytest.mark.parametrize("name, shown", [
    ("op_failed.log", "Timestep too small"),
    ("op_failed.log", "Error: Transient op failed"),
    ("tran_stopped_meas_failed.log", "simulation(s) aborted"),
    ("tran_stopped_meas_failed.log", "meas tran settled when err=0.01 cross=last failed!"),
    ("killed.log", "does not end with ngspice's done line"),
    ("measure_absent_undeclared.log", "meas tran ub when"),
    ("missing_include.log", "Could not find include file"),
    ("error_after_done.log", "meas dc lo when"),
])
def test_a_failed_or_cut_short_run_fails_and_names_the_line(name, shown):
    assert any(shown in line for line in problems((LOGS / name).read_text()))

def test_a_measure_declared_absent_by_the_bench_may_fail():
    text = (LOGS / "measure_absent_undeclared.log").read_text().replace("ngspice-47 done", "may be absent: ub (the output never overshoots past the upper band)\nngspice-47 done")
    assert problems(text) == []
    other = text.replace("may be absent: ub", "may be absent: ua")
    assert problems(other) != []

def test_a_declaration_without_a_reason_does_not_count():
    text = (LOGS / "measure_absent_undeclared.log").read_text().replace("ngspice-47 done", "may be absent: ub\nngspice-47 done")
    assert problems(text) != []

def test_an_empty_log_fails():
    assert problems("") != []

def test_the_command_exits_nonzero_if_any_log_fails():
    script = str(Path(__file__).parent / "spice_log_check.py")
    good = subprocess.run([sys.executable, script, str(LOGS / "clean.log")], capture_output=True, text=True)
    bad = subprocess.run([sys.executable, script, str(LOGS / "clean.log"), str(LOGS / "killed.log")], capture_output=True, text=True)
    assert good.returncode == 0 and bad.returncode == 1 and "killed.log: FAIL" in bad.stdout
