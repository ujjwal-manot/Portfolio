# Tests the session logger and the branch decision rules from the career report.
import csv, pytest
from log_session import log
from decide import decide

def sessions(energy):
    return [{"project": p, "energy": str(e)} for p, e in energy.items()]

def scores(each):
    return [{"project": p, "endurance": s, "debugging": s, "interview": s, "sharing": s} for p, s in each.items()]

def test_log_appends_rows_and_rejects_bad_input(tmp_path):
    f = tmp_path / "sessions.csv"
    log(f, "cpu", 2.5, 4, "yes", "no", "forwarding worked", "load-use bug")
    log(f, "adc", 1, 2, "no", "no", "fft", "corners")
    rows = list(csv.DictReader(f.open()))
    assert [r["project"] for r in rows] == ["cpu", "adc"] and rows[0]["energy"] == "4"
    for bad in [("gpu", 1, 3, "no", "no"), ("cpu", 1, 6, "no", "no"), ("cpu", 0, 3, "no", "no"), ("cpu", 1, 3, "maybe", "no")]:
        with pytest.raises(ValueError):
            log(f, *bad, "", "")

def test_clear_winner_needs_15_percent():
    branch, why = decide(sessions({"fifo_bridge": 5, "cpu": 5, "opamp": 3, "adc": 3}), scores({"fifo_bridge": 5, "cpu": 5, "opamp": 3, "adc": 3}))
    assert branch == "digital" and "rule 1" in why[0]
    branch, why = decide(sessions({"fifo_bridge": 3, "cpu": 3, "opamp": 5, "adc": 5}), scores({"fifo_bridge": 3, "cpu": 3, "opamp": 5, "adc": 5}))
    assert branch == "analog" and "rule 1" in why[0]

def test_close_scores_go_digital():
    branch, why = decide(sessions({"fifo_bridge": 4, "cpu": 4, "opamp": 4, "adc": 4}), scores({"fifo_bridge": 4, "cpu": 4, "opamp": 4, "adc": 5}))
    assert branch == "digital" and "rule 2" in why[0]
    assert any("rule 4" in w for w in why)

def test_low_opamp_energy_rules_out_analog():
    branch, why = decide(sessions({"fifo_bridge": 2, "cpu": 2, "opamp": 2, "adc": 5}), scores({"fifo_bridge": 2, "cpu": 2, "opamp": 5, "adc": 5}))
    assert branch == "digital" and "rule 3" in why[0]
