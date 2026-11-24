# Tests the session logger and the per-track balance of hours and finished checks.
import csv, subprocess, pytest
from log_session import log
from balance import split, behind, finished
from save_result import save

def test_log_appends_rows_with_track_and_rejects_bad_input(tmp_path):
    f = tmp_path / "sessions.csv"
    log(f, "cpu", 2.5, 4, "yes", "no", "forwarding worked", "load-use bug")
    log(f, "adc", 1, 2, "no", "no", "fft", "corners")
    rows = list(csv.DictReader(f.open()))
    assert [(r["project"], r["track"]) for r in rows] == [("cpu", "digital"), ("adc", "ams")] and rows[0]["energy"] == "4"
    for bad in [("gpu", 1, 3, "no", "no"), ("cpu", 1, 6, "no", "no"), ("cpu", 0, 3, "no", "no"), ("cpu", 1, 3, "maybe", "no")]:
        with pytest.raises(ValueError):
            log(f, *bad, "", "")

def test_whole_chip_hours_count_a_third_to_each_track():
    totals = split([{"project": "opamp", "hours": "3"}, {"project": "whole_chip", "hours": "3"}], {"fifo_bridge": 4, "adc": 2})
    assert totals == {"digital": (1.0, 4), "analog": (4.0, 0), "ams": (1.0, 2)}

def test_a_track_more_than_10_percent_behind_the_leader_is_flagged():
    assert behind({"digital": (10, 20), "analog": (9, 18), "ams": (9.5, 19)}) == []
    assert behind({"digital": (10, 20), "analog": (8.9, 20), "ams": (10, 17)}) == [("analog", "hours"), ("ams", "checks")]

def test_only_passing_checks_with_unchanged_sources_count(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    p = tmp_path / "projects/opamp"
    (p / "results").mkdir(parents=True)
    (p / "opamp.cir").write_text("* opamp\n")
    (p / "results/a.log").write_text("ok\n")
    save(p / "results/summary.json", "ac", True, [p / "results/a.log"])
    save(p / "results/summary.json", "noise", False, [p / "results/a.log"])
    assert finished(p, tmp_path) == 1
    (p / "opamp.cir").write_text("* opamp, changed\n")
    assert finished(p, tmp_path) == 0
