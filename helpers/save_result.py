# Records one check result in a summary.json, with the SHA-256 of every raw log behind it.
import hashlib, json, os, sys, time
from pathlib import Path

def save(summary, check, passed, logs, values=None):
    if not logs:
        raise ValueError(f"{check}: a result needs at least one raw log")
    summary = Path(summary)
    hashes = {os.path.relpath(log, summary.parent): hashlib.sha256(Path(log).read_bytes()).hexdigest() for log in logs}
    data = json.loads(summary.read_text()) if summary.exists() else {}
    data[check] = {"result": "pass" if passed else "fail", "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "logs": hashes, "values": values or {}}
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")

if __name__ == "__main__":
    summary, check, code, *logs = sys.argv[1:]
    save(summary, check, code == "0", logs)
    sys.exit(int(code))
