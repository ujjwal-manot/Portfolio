# Checks compare_with_papers/make_report.py: parses real transistor charts.log thresholds, formats all five published.json sections with differences and exact sources, and states honestly whenever a published or measured number is absent.
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_report import parse_charts_vth, build_report

def test_parse_charts_vth_reads_tt_27_short_channel(tmp_path):
    log = tmp_path / "charts.log"
    log.write_text(
        "threshold at 50 mV drain\n"
        "corner   N L=0.13       N L=0.18       P L=0.13\n"
        "tt_27    0.436/0.516     0.379/0.440     0.428/0.461\n",
        encoding="utf-8",
    )
    got = parse_charts_vth(log)
    assert abs(got["VTN10x013"] - 0.516) < 1e-6
    assert abs(got["VTP10x013"] - (-0.461)) < 1e-6

def test_parse_charts_vth_missing_file_returns_empty(tmp_path):
    assert parse_charts_vth(tmp_path / "missing.log") == {}

def test_build_report_covers_all_sections_and_real_diff(tmp_path):
    here = Path(__file__).resolve().parent
    pub_path = here / "published.json"
    fake_repo = tmp_path / "repo"
    charts = fake_repo / "projects" / "opamp" / "results" / "charts.log"
    charts.parent.mkdir(parents=True)
    charts.write_text(
        "corner   N L=0.13   P L=0.13\n"
        "tt_27    0.436/0.516   0.428/0.461\n",
        encoding="utf-8",
    )
    md = build_report(pub_path, fake_repo)
    assert "\u2014" not in md
    assert "VTN10x013" in md and "0.516" in md and "+0.016" in md
    assert "VTP10x013" in md and "-0.461" in md and "+0.009" in md
    assert "not published" in md
    assert "not run yet" in md
    assert "Murmann" in md and "Cummings" in md and "JKU" in md
