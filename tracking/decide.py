# Applies the career report's four decision rules to sessions.csv and scores.csv.
import csv, statistics
from pathlib import Path

DIGITAL, ANALOG = ["fifo_bridge", "cpu"], ["opamp", "adc"]

def decide(session_rows, score_rows):
    energy = {p: statistics.mean(int(r["energy"]) for r in session_rows if r["project"] == p) for p in DIGITAL + ANALOG}
    total = {r["project"]: energy[r["project"]] + sum(int(r[k]) for k in ["endurance", "debugging", "interview", "sharing"])
             for r in score_rows if r["project"] in energy}
    digital, analog = sum(total[p] for p in DIGITAL), sum(total[p] for p in ANALOG)
    if energy["opamp"] <= 2:
        why = [f"rule 3: opamp energy {energy['opamp']:.1f} <= 2 rules out analog"]
        branch = "digital"
    elif max(digital, analog) >= 1.15 * min(digital, analog):
        branch = "digital" if digital > analog else "analog"
        why = [f"rule 1: {branch} wins {max(digital, analog):.1f} to {min(digital, analog):.1f}, at least 15% ahead"]
    else:
        branch = "digital"
        why = [f"rule 2: {digital:.1f} vs {analog:.1f} is within 15%, so digital, keeping AMS verification as a bridge"]
    if max(total, key=total.get) == "adc":
        why.append("rule 4: adc is the top project, consider data converter design")
    return branch, why

if __name__ == "__main__":
    here = Path(__file__).parent
    branch, why = decide(list(csv.DictReader((here / "sessions.csv").open())), list(csv.DictReader((here / "scores.csv").open())))
    print(branch, *why, sep="\n")
