# Fails if the repo fakes results, keeps results older than their sources, names a file in a uses.txt that does not exist, quotes README numbers its logs never show, hides failures, presets a measured or recomputed value to a constant in a SPICE bench (a failed run would keep it; a counter stepped only from itself is fine), uses toy models, simulates a circuit in Python (a solver import, or a loop stepping a capacitor voltage through time), or breaks the one-comment-per-file rule.
import ast, hashlib, io, json, re, sys, tokenize
from pathlib import Path
from save_result import sources

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


TIME_STEP = re.compile(r"^(dt|t_?step\w*|period\w*|step_s|h)$")
CAPACITOR = re.compile(r"^(c|cap\w*|c_\w+|\w+_cap|\w+_f)$")

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
        if isinstance(node, (ast.For, ast.While)):
            for step in ast.walk(node):
                if isinstance(step, (ast.Assign, ast.AugAssign)):
                    targets = {ast.unparse(x) for x in (step.targets if isinstance(step, ast.Assign) else [step.target])}
                    names = {ast.unparse(x) for x in ast.walk(step.value) if isinstance(x, (ast.Name, ast.Attribute))}
                    divisors = {ast.unparse(x.right) for x in ast.walk(step.value) if isinstance(x, ast.BinOp) and isinstance(x.op, ast.Div)}
                    if (isinstance(step, ast.AugAssign) or targets & names) and any(TIME_STEP.search(n) for n in names) and any(CAPACITOR.search(d) for d in divisors):
                        yield "python_simulation", f"line {step.lineno} steps a capacitor voltage through time"
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            names = {a.name for a in node.names} if isinstance(node, ast.ImportFrom) else set()
            if any(m.startswith(SIM_MODULES) for m in mods) or (any(m.startswith("scipy.signal") for m in mods) and names & SIM_NAMES):
                yield "python_simulation", f"line {node.lineno} imports a circuit solver"


def missing_uses(project, root):
    uses = project / "uses.txt"
    return [line.strip() for line in (uses.read_text().splitlines() if uses.exists() else []) if line.strip() and not (root / line.strip()).exists()]

def summary_problems(path, root):
    missing = missing_uses(path.resolve().parent.parent, root.resolve())
    for name in missing:
        yield "missing_use", f"uses.txt names a file that does not exist, so no result here can be checked for staleness: {name}"
    if missing:
        return
    now = sources(path.resolve().parent.parent, root.resolve())
    for check, entry in json.loads(path.read_text()).items():
        then = entry.get("sources", {})
        changed = sorted(f for f in now.keys() | then.keys() if now.get(f) != then.get(f))
        if changed:
            yield "stale_result", f"{check} is older than {', '.join(changed[:3])}" + (f" and {len(changed) - 3} more" if len(changed) > 3 else "")
        if entry["result"] == "pass" and not entry["logs"]:
            yield "bad_log", f"{check} passes with no raw log"
        for log, digest in entry["logs"].items():
            log_path = path.parent / log
            if not log_path.exists():
                yield "bad_log", f"{check}: {log} is missing"
            elif hashlib.sha256(log_path.read_bytes()).hexdigest() != digest:
                yield "bad_log", f"{check}: {log} changed after the result was saved"


NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?:[eE][-+]?\d+)?(?![\w.])")


WORD = re.compile(r"[a-z][a-z0-9_]{2,}")
COMMON = {"and", "the", "with", "for", "from", "per", "all", "one", "both", "than", "each", "every", "after", "over", "under", "pass"}


def shown(claim, logged):
    if claim in logged:
        return True
    mantissa, _, exponent = claim.lower().partition("e")
    figures = len(mantissa.replace(".", "").lstrip("0"))
    step = 10 ** (-len(mantissa.partition(".")[2]) + int(exponent or 0))
    return figures >= 3 and any(abs(float(v) - float(claim)) <= step / 2 * (1 + 1e-9) for v in logged)


def labels(text):
    return set(WORD.findall(text.lower())) - COMMON


def readme_problems(path):
    where = None
    for line in path.read_text().splitlines():
        if not line.startswith("|"):
            where = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if where is None:
            where, spec = cells[-1] == "Where", cells[-1] in ("Value", "Target")
            continue
        if set(line) <= set("|-: "):
            continue
        if not where:
            if not spec and (path.parent / "results").is_dir() and any(NUMBER.search(c) for c in cells[1:]):
                yield "readme_claim", f"row '{cells[0]}' quotes numbers in a table with no Where column"
            continue
        logs = re.findall(r"`(results/[^`]+)`", cells[-1])
        found = [p for pattern in logs for p in sorted(path.parent.glob(pattern))]
        if not found:
            yield "readme_claim", f"row '{cells[0]}' names no log" if not logs else f"{', '.join(logs)} does not exist"
            continue
        lines = [(labels(l), set(NUMBER.findall(l))) for p in found for l in p.read_text(errors="replace").splitlines()]
        for piece in (s for cell in cells[1:-1] for s in re.split(r"[,;]", cell)):
            words = labels(piece) or labels(cells[0])
            for claim in NUMBER.findall(piece):
                if not any(words & w and shown(claim, n) for w, n in lines):
                    yield "readme_claim", f"says {claim} in row '{cells[0]}', and no line of {', '.join(logs)} shows it next to {', '.join(sorted(words)) or 'a label'}"


def silent_defaults(text):
    constant = re.compile(r"[-+]?[0-9.]+(?:e[-+]?\d+)?$", re.I)
    lets = [(m.group(1), m.group(2).strip()) for m in re.finditer(r"^\s*let\s+(\w+)\s*=(.*)$", text, re.M | re.I)]
    measured = set(re.findall(r"^\s*meas\s+\w+\s+(\w+)\b", text, re.M | re.I))
    absent = set(re.findall(r"may be absent: (\w+) \(\S", text))
    from_run = lambda value: re.search(r"\b[vi]\(|\btime\b", value, re.I) or set(re.findall(r"[a-z_]\w*", value, re.I)) & measured
    first = {}
    for name, value in lets:
        first.setdefault(name, value)
    preset = [name for name, value in first.items() if constant.match(value)]
    return [name for name in preset if (name in measured and name not in absent) or any(n == name and from_run(v) for n, v in lets)]

def find_problems(root):
    root = Path(root)
    problems = []
    for path in files(root):
        rel = path.relative_to(root)
        if path.name == "README.md":
            problems += [(rule, rel, why) for rule, why in readme_problems(path)]
        if path.name == "summary.json":
            problems += [(rule, rel, why) for rule, why in summary_problems(path, root)]
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
            problems += [("silent_default", rel, f"{name} is preset to a constant and later measured or recomputed, so a failed run keeps the preset") for name in silent_defaults(text)]
        if path.suffix == ".py":
            problems += [(rule, rel, why) for rule, why in python_problems(path, text)]
        if path.name == "Makefile" or path.suffix == ".mk":
            problems += [("hidden_failure", rel, l.strip()) for l in text.splitlines() if "|| true" in l or re.search(r"\bthen :", l) or re.match(r"\t-\S", l) or l.startswith(".IGNORE")]
    return problems


if __name__ == "__main__":
    found = find_problems(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent)
    for rule, path, why in found:
        print(f"{rule:18} {path}: {why}")
    print(f"{len(found)} problems")
    sys.exit(1 if found else 0)
