# Records one check result in a summary.json, with the SHA-256 of every raw log behind it and of every source it was made from: the project's files that git tracks or would track (so ignored build byproducts never count), plus each helper those files name, directly or through another helper; a lock file beside the summary lets parallel make jobs save without losing entries.
import fcntl, hashlib, json, os, re, subprocess, sys, time
from pathlib import Path

def sources(project, root):
    project = project if root in (project, *project.parents) else root
    dirs = [str(d.relative_to(root)) for d in (project, root / "helpers") if d.exists()]
    listed = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "--", *dirs], cwd=root, capture_output=True, text=True, check=True).stdout.splitlines()
    files = {root / n for n in listed if (root / n).is_file() and Path(n).name != "README.md" and "results" not in Path(n).parts}
    helpers = {f for f in files if project not in f.parents and project != root}
    keep = files - helpers
    while True:
        text = "\n".join(f.read_bytes().decode(errors="ignore") for f in keep)
        used = {h for h in helpers if re.search(rf"\b{re.escape(h.stem)}\b", text)}
        if used <= keep:
            break
        keep |= used
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(keep)}

def save(summary, check, passed, logs, values=None, root=None):
    if not logs:
        raise ValueError(f"{check}: a result needs at least one raw log")
    summary = Path(summary).resolve()
    project = summary.parent.parent
    hashes = {os.path.relpath(Path(log).resolve(), summary.parent): hashlib.sha256(Path(log).read_bytes()).hexdigest() for log in logs}
    here = next(d for d in summary.parents if d.exists())
    root = Path(root).resolve() if root else Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=here, capture_output=True, text=True, check=True).stdout.strip())
    entry = {"result": "pass" if passed else "fail", "time": time.strftime("%Y-%m-%d %H:%M:%S"),
             "logs": hashes, "values": values or {}, "sources": sources(project, root)}
    summary.parent.mkdir(parents=True, exist_ok=True)
    with open(summary.with_name(summary.name + ".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = json.loads(summary.read_text()) if summary.exists() else {}
        data[check] = entry
        summary.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")

if __name__ == "__main__":
    summary, check, code, *logs = sys.argv[1:]
    save(summary, check, code == "0", logs)
    sys.exit(int(code))
