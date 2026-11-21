# Records one check result in a summary.json, with the SHA-256 of every raw log behind it and of every source it was made from (the project's and helpers/ files that git tracks or would track, so ignored build byproducts never count).
import hashlib, json, os, subprocess, sys, time
from pathlib import Path

def sources(project, root):
    project = project if root in (project, *project.parents) else root
    dirs = [str(d.relative_to(root)) for d in (project, root / "helpers") if d.exists()]
    listed = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "--", *dirs], cwd=root, capture_output=True, text=True, check=True).stdout.splitlines()
    keep = {root / n for n in listed if (root / n).is_file() and Path(n).name != "README.md" and "results" not in Path(n).parts}
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(keep)}

def save(summary, check, passed, logs, values=None, root=None):
    if not logs:
        raise ValueError(f"{check}: a result needs at least one raw log")
    summary = Path(summary).resolve()
    project = summary.parent.parent
    hashes = {os.path.relpath(Path(log).resolve(), summary.parent): hashlib.sha256(Path(log).read_bytes()).hexdigest() for log in logs}
    here = next(d for d in summary.parents if d.exists())
    root = Path(root).resolve() if root else Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=here, capture_output=True, text=True, check=True).stdout.strip())
    data = json.loads(summary.read_text()) if summary.exists() else {}
    data[check] = {"result": "pass" if passed else "fail", "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "logs": hashes, "values": values or {}, "sources": sources(project, root)}
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")

if __name__ == "__main__":
    summary, check, code, *logs = sys.argv[1:]
    save(summary, check, code == "0", logs)
    sys.exit(int(code))
