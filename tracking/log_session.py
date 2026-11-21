# Appends one work session to sessions.csv: python3 log_session.py cpu 2.5 4 yes no "best moment" "worst moment"
import csv, datetime, sys
from pathlib import Path
from balance import TRACK

PROJECTS = [*TRACK, "whole_chip"]
FIELDS = ["date", "project", "track", "hours", "energy", "lost_track_of_time", "extra_work", "best", "worst"]

def log(path, project, hours, energy, lost_track, extra, best, worst):
    hours, energy = float(hours), int(energy)
    if project not in PROJECTS or not 0 < hours <= 16 or not 1 <= energy <= 5 or {lost_track, extra} - {"yes", "no"}:
        raise ValueError(f"project one of {PROJECTS}, hours 0-16, energy 1-5, yes/no for the two questions")
    path = Path(path)
    new = not path.exists()
    with path.open("a", newline="") as f:
        out = csv.DictWriter(f, FIELDS)
        if new:
            out.writeheader()
        out.writerow(dict(zip(FIELDS, [datetime.date.today(), project, TRACK.get(project, "all"), hours, energy, lost_track, extra, best, worst])))

if __name__ == "__main__":
    log(Path(__file__).parent / "sessions.csv", *sys.argv[1:])
