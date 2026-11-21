# Tests that save_result records results with correct log hashes and the hashes of git-visible sources only, and refuses results without logs.
import hashlib, json, subprocess, sys, pytest
from pathlib import Path
from save_result import save

def test_records_pass_with_hash(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    log = tmp_path / "logs" / "run.log"
    log.parent.mkdir()
    log.write_text("all good\n")
    save(tmp_path / "summary.json", "gain", True, [log], {"gain_db": 68.1})
    entry = json.loads((tmp_path / "summary.json").read_text())["gain"]
    assert entry["result"] == "pass"
    assert entry["values"] == {"gain_db": 68.1}
    assert entry["logs"] == {"logs/run.log": hashlib.sha256(b"all good\n").hexdigest()}

def test_refuses_missing_or_no_logs(tmp_path):
    with pytest.raises(FileNotFoundError):
        save(tmp_path / "s.json", "x", True, [tmp_path / "nope.log"])
    with pytest.raises(ValueError):
        save(tmp_path / "s.json", "x", True, [])

def test_command_line_passes_exit_code_through(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    log = tmp_path / "a.log"
    log.write_text("boom")
    r = subprocess.run([sys.executable, "save_result.py", str(tmp_path / "s.json"), "sim", "3", str(log)], cwd=Path(__file__).parent)
    assert r.returncode == 3
    assert json.loads((tmp_path / "s.json").read_text())["sim"]["result"] == "fail"

def test_records_hash_of_every_source(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("build/\n*.result.xml\n")
    for name in ("proj/design/a.sv", "proj/tests/t.py", "proj/tests/t.result.xml", "proj/README.md", "proj/build/x.v", "helpers/h.py", "other/o.sv"):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(name)
    log = tmp_path / "proj/results/run.log"
    log.parent.mkdir()
    log.write_text("ok")
    save(tmp_path / "proj/results/summary.json", "sim", True, [log], root=tmp_path)
    entry = json.loads((tmp_path / "proj/results/summary.json").read_text())["sim"]
    assert entry["sources"] == {n: hashlib.sha256(n.encode()).hexdigest() for n in ("helpers/h.py", "proj/design/a.sv", "proj/tests/t.py")}
