# Tests that save_result records results with correct log hashes, hashes the project's git-visible sources plus only the helpers they use (directly or through another helper), refuses results without logs, and keeps every entry when many checks save at once (make -j).
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

def test_records_hash_of_every_source_and_used_helper(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("build/\n*.result.xml\n")
    files = {"proj/design/a.sv": "module a; endmodule", "proj/tests/t.py": "from used import f", "proj/tests/t.result.xml": "x",
             "proj/README.md": "readme", "proj/build/x.v": "x", "helpers/used.py": "import deep", "helpers/deep.py": "x = 1",
             "helpers/unused.py": "y = 2", "other/o.sv": "o"}
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    log = tmp_path / "proj/results/run.log"
    log.parent.mkdir()
    log.write_text("ok")
    save(tmp_path / "proj/results/summary.json", "sim", True, [log], root=tmp_path)
    entry = json.loads((tmp_path / "proj/results/summary.json").read_text())["sim"]
    kept = ("helpers/deep.py", "helpers/used.py", "proj/design/a.sv", "proj/tests/t.py")
    assert entry["sources"] == {n: hashlib.sha256(files[n].encode()).hexdigest() for n in kept}

def test_parallel_saves_keep_every_entry(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    log = tmp_path / "run.log"
    log.write_text("ok\n")
    script = Path(__file__).with_name("save_result.py")
    runs = [subprocess.Popen([sys.executable, str(script), str(tmp_path / "summary.json"), f"check_{i}", "0", str(log)], cwd=tmp_path) for i in range(24)]
    assert all(r.wait() == 0 for r in runs)
    assert sorted(json.loads((tmp_path / "summary.json").read_text())) == sorted(f"check_{i}" for i in range(24))
