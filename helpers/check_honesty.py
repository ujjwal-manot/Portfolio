# Fails if the repo fakes results, hides failures, uses toy models, or breaks the one-comment-per-file rule.
import ast, hashlib, io, json, re, sys, tokenize
from pathlib import Path

SKIP = {".git", "node_modules", "build", "sim_build", "runs", "dist", "__pycache__", "third_party"}
SPICE = {".sp", ".spice", ".cir"}
SLASH = {".sv", ".v", ".svh", ".c", ".h", ".ts", ".tsx", ".js", ".ld", ".S"}
HASH = {".py", ".sh", ".tcl", ".sby", ".ys", ".yml", ".yaml", ".mk"}
RANDOM_CALLS = re.compile(r"^(np|numpy)\.random\.|^random\.")
SIM_MODULES = ("scipy.integrate", "PySpice", "ahkab", "lcapy")
SIM_NAMES = {"odeint", "solve_ivp", "lsim", "dlsim", "lti", "dlti"}
FALLBACK_ERRORS = {None, "FileNotFoundError", "OSError", "ImportError", "Exception", "BaseException"}


def files(root):
    for path in sorted(root.rglob("*")):
        if path.is_file() and not SKIP & set(path.relative_to(root).parts):
            yield path


def comment_lines(path, text):
    if path.suffix == ".py":
        toks = tokenize.generate_tokens(io.StringIO(text).readline)
        return len({t.start[0] for t in toks if t.type == tokenize.COMMENT and not (t.start[0] == 1 and t.string.startswith("#!"))})
    lines = text.splitlines()
    if path.suffix in SPICE:
        return 1 + sum(1 for l in lines[1:] if l.lstrip().startswith("*") or re.search(r"\s[;$]\s", l))
    if path.suffix in SLASH:
        code = re.sub(r'"(\\.|[^"\\])*"', '""', text)
        count, inside = 0, False
        for line in code.splitlines():
            if inside or "//" in line or "/*" in line:
                count += 1
            inside = (inside or "/*" in line) and "*/" not in line.split("/*")[-1]
        return count
    if path.suffix in HASH or path.name == "Makefile":
        return sum(1 for i, l in enumerate(lines) if re.match(r"\s*#(?!!)", l) or (i and re.search(r"\s#\s", l) and not l.lstrip().startswith("#")))
    return None


def python_problems(path, text):
    tree = ast.parse(text)
    in_helpers = bool({"helpers", "compare_with_papers"} & set(path.parts)) and not path.name.startswith("test_")
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            name = node.type.id if isinstance(node.type, ast.Name) else (None if node.type is None else "other")
            if name in FALLBACK_ERRORS and all(isinstance(b, (ast.Pass, ast.Return, ast.Continue)) for b in node.body):
                yield "fake_fallback", f"line {node.lineno} swallows {name or 'every error'}"
        if in_helpers and isinstance(node, ast.Call) and RANDOM_CALLS.match(ast.unparse(node.func)):
            yield "made_up_numbers", f"line {node.lineno} calls {ast.unparse(node.func)}"
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            names = {a.name for a in node.names} if isinstance(node, ast.ImportFrom) else set()
            if any(m.startswith(SIM_MODULES) for m in mods) or (any(m.startswith("scipy.signal") for m in mods) and names & SIM_NAMES):
                yield "python_simulation", f"line {node.lineno} imports a circuit solver"


def summary_problems(path):
    for check, entry in json.loads(path.read_text()).items():
        if entry["result"] == "pass" and not entry["logs"]:
            yield "bad_log", f"{check} passes with no raw log"
        for log, digest in entry["logs"].items():
            log_path = path.parent / log
            if not log_path.exists():
                yield "bad_log", f"{check}: {log} is missing"
            elif hashlib.sha256(log_path.read_bytes()).hexdigest() != digest:
                yield "bad_log", f"{check}: {log} changed after the result was saved"


def find_problems(root):
    root = Path(root)
    problems = []
    for path in files(root):
        rel = path.relative_to(root)
        if path.name == "summary.json":
            problems += [(rule, rel, why) for rule, why in summary_problems(path)]
            continue
        if "results" in rel.parts:
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        count = comment_lines(path, text)
        if count is not None and count != 1:
            problems.append(("comments", rel, f"{count} comment lines, needs exactly 1"))
        if path.suffix in SPICE:
            problems += [("toy_model", rel, l.strip()) for l in text.splitlines() if re.match(r"\s*\.model\s+\S+\s+[np]mos", l, re.I)]
        if path.suffix == ".py":
            problems += [(rule, rel, why) for rule, why in python_problems(path, text)]
        if path.name == "Makefile" or path.suffix == ".mk":
            problems += [("hidden_failure", rel, l.strip()) for l in text.splitlines() if "|| true" in l or re.match(r"\t-\S", l) or l.startswith(".IGNORE")]
    return problems


if __name__ == "__main__":
    found = find_problems(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent)
    for rule, path, why in found:
        print(f"{rule:18} {path}: {why}")
    print(f"{len(found)} problems")
    sys.exit(1 if found else 0)
