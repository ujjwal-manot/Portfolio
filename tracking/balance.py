# Reports hours (from sessions.csv) and finished checks (passing results whose sources are unchanged) per track, and fails if any track is more than 10% behind the leader; whole_chip hours count a third to each track.
import csv, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "helpers"))
from save_result import sources

TRACKS = {"digital": ["fifo_bridge", "cpu", "tensor_core", "coherent_noc"],
          "analog": ["opamp", "bandgap_ldo", "serdes_frontend", "lc_vco"],
          "ams": ["adc", "power_manager", "serdes_link", "frac_n_pll"]}
TRACK = {p: t for t, ps in TRACKS.items() for p in ps}

def split(sessions, checks):
    hours = dict.fromkeys(TRACKS, 0.0)
    for r in sessions:
        for t in TRACKS if r["project"] == "whole_chip" else [TRACK[r["project"]]]:
            hours[t] += float(r["hours"]) / (3 if r["project"] == "whole_chip" else 1)
    return {t: (hours[t], sum(checks.get(p, 0) for p in TRACKS[t])) for t in TRACKS}

def behind(totals):
    return [(t, m) for i, m in enumerate(("hours", "checks")) for t in TRACKS if totals[t][i] < 0.9 * max(v[i] for v in totals.values())]

def finished(project, root):
    summary = project / "results" / "summary.json"
    if not summary.exists():
        return 0
    now = sources(project, root)
    return sum(e["result"] == "pass" and e.get("sources") == now for e in json.loads(summary.read_text()).values())

if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    log = root / "tracking" / "sessions.csv"
    totals = split(list(csv.DictReader(log.open())) if log.exists() else [], {p: finished(root / "projects" / p, root) for p in TRACK})
    for t, (h, c) in totals.items():
        print(f"{t:8} {h:6.1f} hours {c:4} finished checks")
    for t, m in behind(totals):
        print(f"{t} is more than 10% behind on {m}")
    sys.exit(1 if behind(totals) else 0)
