# Fails if the repo fakes results, keeps results older than their sources, names a file in a uses.txt that does not exist, quotes README numbers its logs never show, hides failures, presets a measured or run-derived value to a constant in a SPICE bench however it is spelled or chained (a failed run would keep it; counters, clamps, search brackets and nan presets are fine), measures inside a loop without a nan reset (a real overflow nan defined before the first analysis) or destroy all in the innermost loop (a failed meas keeps the last pass's value), runs ngspice from a Makefile other than through helpers/ngspice.sh (which fails the run unless spice_log_check passes its log) or lets a failed wrapper run pass (a leading -, .IGNORE, make -i or -k, a result recorded as zero or only echoed, or an if with no branch that sets a nonzero flag, exits nonzero or appends to a failed file that the Makefile then reads; whether the recorded failure then reaches the saved verdict is left to save_result and summary.json), uses toy models, simulates a circuit in Python (a solver import, or a loop stepping a capacitor voltage through time), or breaks the one-comment-per-file rule.
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


MEAS = r"^\s*meas(?:ure)?\s+\w+\s+(\w+)\b"
ANALYSIS = re.compile(r"^\s*(tran|ac|dc|op|noise|run|pz|sens|disto)\b", re.I)

def run_derived(lets, measured):
    derived = set(measured)
    while True:
        new = {name for name, value in lets if re.search(r"\b[vi]\(|\btime\b", value, re.I) or set(re.findall(r"[a-z_]\w*", value, re.I)) & derived} - derived
        if not new:
            return derived
        derived |= new

def real_nans(text):
    lines = text.splitlines()
    first = next((i for i, line in enumerate(lines) if ANALYSIS.match(line)), len(lines))
    nans = set()
    for i, line in enumerate(lines[:first]):
        m = re.match(r"\s*let\s+(\w+)\s*=\s*\(?\s*1e(\d+)\s*-\s*1e(\d+)\s*\)?\s*$", line, re.I)
        if m and int(m.group(2)) >= 309 and int(m.group(3)) >= 309:
            nans.add(m.group(1))
    return nans

def silent_defaults(text):
    lets = [(m.group(1), m.group(2).strip()) for m in re.finditer(r"^\s*let\s+(\w+)\s*=(.*)$", text, re.M | re.I)]
    measured = set(re.findall(MEAS, text, re.M | re.I))
    absent = set(re.findall(r"may be absent: (\w+) \(\S", text))
    nans = real_nans(text)
    derived = run_derived(lets, measured)
    names = lambda value: set(re.findall(r"[a-z_]\w*", value, re.I))
    first = {}
    for name, value in lets:
        first.setdefault(name, value)
    preset = [name for name, value in first.items() if name not in nans and not names(value) & (derived | nans) and not re.search(r"\b[vi]\(|\btime\b", value, re.I)]
    return [name for name in preset if (name in measured and name not in absent) or any(n == name and (names(v) & derived - {name} or re.search(r"\b[vi]\(|\btime\b", v, re.I)) for n, v in lets)]

def stale_measures(text):
    nans, found, stack = real_nans(text), [], []
    for line in text.splitlines():
        word = line.strip().split(" ", 1)[0].lower()
        if word in ("while", "repeat", "dowhile", "foreach", "if"):
            stack.append((word != "if", set()))
        elif word == "end" and stack:
            stack.pop()
        elif stack and re.match(r"destroy\s+all\b", line.strip(), re.I):
            stack[-1][1].add("*")
        elif stack and (m := re.match(r"\s*let\s+(\w+)\s*=\s*(\w+)\s*$", line)) and m.group(2) in nans:
            stack[-1][1].add(m.group(1))
        elif stack and (m := re.match(MEAS, line, re.I)):
            seen, in_loop = set(), False
            for is_loop, resets in reversed(stack):
                seen |= resets
                if is_loop:
                    in_loop = True
                    break
            if in_loop and not {"*", m.group(1)} & seen:
                found.append(m.group(1))
    return found

DIRECT = re.compile(r"(?<![\w./-])ngspice\s+(?!vlnggen\b|-v\b)")
WRAPPER = re.compile(r"^(\w+)\s*[:?+]?=.*helpers/ngspice\.sh")

FAILS = r"(?:\w+=[1-9]\d*\b|exit\s+[1-9]\d*\b|false\b|>>\s*\S*failed\S*)"

def unchecked_log(text):
    names = set(re.findall(WRAPPER.pattern, text, re.M))
    call = re.compile("(?:" + "|".join([r"\S*helpers/ngspice\.sh"] + [re.escape(f"$({n})") for n in names]) + r")[^;&|()\n]*")
    found = []
    for line in re.sub(r"\\\n\s*", " ", text).splitlines():
        if line.lstrip().startswith("#") or WRAPPER.match(line):
            continue
        if DIRECT.search(line):
            found.append(f"runs ngspice directly, so its log is never checked: {line.strip()}")
            continue
        for m in call.finditer(line):
            before, after = line[:m.start()], line[m.end():]
            rest = after.lstrip(") \t")
            cond = re.search(r"\bif\s+(!?)[^;]*$", before)
            if cond:
                block = re.split(r"\bfi\b", after, maxsplit=1)[0]
                parts = re.split(r"\belse\b", block, maxsplit=1)
                branch = parts[0] if cond.group(1) else (parts[1] if len(parts) > 1 else "")
                ok = re.search(FAILS, branch)
            elif rest.startswith("||"):
                ok = re.match(r"\|\|\s*" + FAILS, rest)
            else:
                ok = rest == "" or (rest.startswith("&&") and not re.search(r"\|\|(?!\s*" + FAILS + ")", rest))
            if not ok:
                found.append(f"does not fail on the checked run's exit code: {line.strip()}")
    for name in sorted(set(re.findall(r">>\s*([\w$/.-]*failed[\w.]*)", text))):
        if not any(name in line and not re.search(r">>\s*" + re.escape(name), line) for line in text.splitlines()):
            found.append(f"appends failed runs to {name} but never reads it, so they never reach a verdict")
    return found

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
            problems += [("stale_meas", rel, f"{name} is measured inside a loop without a nan reset or destroy all before it, so a failed meas keeps the last pass's value") for name in stale_measures(text)]
        if path.suffix == ".py":
            problems += [(rule, rel, why) for rule, why in python_problems(path, text)]
        if path.name == "Makefile" or path.suffix == ".mk":
            problems += [("hidden_failure", rel, l.strip()) for l in text.splitlines() if "|| true" in l or re.search(r"\bthen :", l) or re.match(r"\t@?-\S", l) or l.startswith(".IGNORE") or re.match(r"\s*MAKEFLAGS\s*[+:?]?=.*(?<!\S)-\w*[ik]", l)]
            problems += [("unchecked_log", rel, why) for why in unchecked_log(text)]
    return problems


if __name__ == "__main__":
    found = find_problems(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent)
    for rule, path, why in found:
        print(f"{rule:18} {path}: {why}")
    print(f"{len(found)} problems")
    sys.exit(1 if found else 0)
