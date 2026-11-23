# Checks spice_log_check on real ngspice logs kept in fixtures/spice_logs: a clean run and one that converged after its dynamic gmin stepping failed pass, while an operating point that never converged, a transient that stopped with a failed meas, and a run killed partway (no closing done line) each fail with the line that shows why.
import subprocess, sys
from pathlib import Path
import pytest
from spice_log_check import problems

LOGS = Path(__file__).parent / "fixtures" / "spice_logs"

@pytest.mark.parametrize("name", ["clean.log", "converged_after_gmin_failed.log"])
def test_a_run_that_finished_cleanly_passes(name):
    assert problems((LOGS / name).read_text()) == []

@pytest.mark.parametrize("name, shown", [
    ("op_failed.log", "Timestep too small"),
    ("op_failed.log", "source stepping failed"),
    ("tran_stopped_meas_failed.log", "simulation(s) aborted"),
    ("tran_stopped_meas_failed.log", "meas tran settled when err=0.01 cross=last failed!"),
    ("killed.log", "does not end with ngspice's done line"),
])
def test_a_failed_or_cut_short_run_fails_and_names_the_line(name, shown):
    assert any(shown in line for line in problems((LOGS / name).read_text()))

def test_an_empty_log_fails():
    assert problems("") != []

def test_the_command_exits_nonzero_if_any_log_fails():
    script = str(Path(__file__).parent / "spice_log_check.py")
    good = subprocess.run([sys.executable, script, str(LOGS / "clean.log")], capture_output=True, text=True)
    bad = subprocess.run([sys.executable, script, str(LOGS / "clean.log"), str(LOGS / "killed.log")], capture_output=True, text=True)
    assert good.returncode == 0 and bad.returncode == 1 and "killed.log: FAIL" in bad.stdout
