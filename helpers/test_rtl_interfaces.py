# Verifies RTL port-interface consistency across cocotb testbenches and SymbiYosys formal harnesses, checking every dut.<port> access and .port() binding against the target Verilog or SystemVerilog module declaration.
import ast
import os
import re
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
IGNORED_COCOTB_ATTRS = {"_log", "_name", "_path", "_id", "_fullname", "_type"}
PORT_DIRECTIONS = {"input", "output", "inout"}
PORT_TYPE_WORDS = {"logic", "wire", "reg", "bit", "signed", "unsigned", "var", "tri"}

FLAGSHIP_COCOTB = [
    (
        "projects/frac_n_pll/tests/test_mash111_cocotb.py",
        {
            "mash111": "projects/frac_n_pll/design/mash111.sv",
            "pfd_div": "projects/frac_n_pll/design/pfd_div.sv",
        },
    ),
    (
        "projects/serdes_link/tests/test_serdes_cocotb.py",
        {
            "prbs": "projects/serdes_link/design/prbs.sv",
            "dfe_lms": "projects/serdes_link/design/dfe_lms.sv",
            "bb_cdr": "projects/serdes_link/design/bb_cdr.sv",
            "pam4_slicer": "projects/serdes_link/design/pam4_slicer.sv",
        },
    ),
    (
        "projects/coherent_noc/tests/test_noc_cocotb.py",
        {
            "xy_router": "projects/coherent_noc/design/xy_router.sv",
            "d2d_replay": "projects/coherent_noc/design/d2d_replay.sv",
            "mesi_dir": "projects/coherent_noc/design/mesi_dir.sv",
        },
    ),
    ("compare_with_papers/cummings_fifo/test_cummings_cocotb.py", {"fifo1": "compare_with_papers/cummings_fifo/fifo1.v"}),
]

FLAGSHIP_FORMAL = [
    (
        "projects/coherent_noc/formal/noc_rules.sby",
        "projects/coherent_noc/formal/noc_rules.sv",
        {
            "xy_router": "projects/coherent_noc/design/xy_router.sv",
            "d2d_replay": "projects/coherent_noc/design/d2d_replay.sv",
            "mesi_dir": "projects/coherent_noc/design/mesi_dir.sv",
        },
    ),
    (
        "compare_with_papers/cummings_fifo/formal/cummings.sby",
        "compare_with_papers/cummings_fifo/formal/cummings_formal.sv",
        {
            "fifo1": "compare_with_papers/cummings_fifo/fifo1.v",
            "fifomem": "compare_with_papers/cummings_fifo/fifomem.v",
            "sync_r2w": "compare_with_papers/cummings_fifo/sync_r2w.v",
            "sync_w2r": "compare_with_papers/cummings_fifo/sync_w2r.v",
            "rptr_empty": "compare_with_papers/cummings_fifo/rptr_empty.v",
            "wptr_full": "compare_with_papers/cummings_fifo/wptr_full.v",
        },
    ),
]


def strip_sv_comments(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def _matching_paren(text, open_idx):
    depth = 0
    for idx in range(open_idx, len(text)):
        if text[idx] == "(":
            depth += 1
        elif text[idx] == ")":
            depth -= 1
            if depth == 0:
                return idx
    raise ValueError("unbalanced parentheses in module header")


def _extract_ports_from_header(header):
    ports = set()
    for raw_item in header.split(","):
        item = re.sub(r"\[[^\]]*\]", " ", raw_item)
        item = re.sub(r"=.*", "", item).strip()
        if not item:
            continue
        tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_$]*", item)
        if not tokens:
            continue
        name = tokens[-1]
        if name not in PORT_DIRECTIONS and name not in PORT_TYPE_WORDS:
            ports.add(name)
    return ports


def parse_sv_modules(text):
    clean = strip_sv_comments(text)
    modules = {}
    pos = 0
    pattern = re.compile(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)")
    while True:
        m = pattern.search(clean, pos)
        if not m:
            break
        mod_name = m.group(1)
        idx = m.end()
        while idx < len(clean) and clean[idx].isspace():
            idx += 1
        if idx < len(clean) and clean[idx] == "#":
            idx += 1
            while idx < len(clean) and clean[idx].isspace():
                idx += 1
            if idx < len(clean) and clean[idx] == "(":
                idx = _matching_paren(clean, idx) + 1
        while idx < len(clean) and clean[idx].isspace():
            idx += 1
        ports = set()
        if idx < len(clean) and clean[idx] == "(":
            close_idx = _matching_paren(clean, idx)
            ports = _extract_ports_from_header(clean[idx + 1 : close_idx])
            pos = close_idx + 1
        else:
            pos = idx
        modules[mod_name] = ports
    return modules


def check_sv_balance(text):
    clean = re.sub(r'"(\\.|[^"\\])*"', '""', strip_sv_comments(text))
    pairs = {"(": ")", "[": "]", "{": "}"}
    stack = []
    for ch in clean:
        if ch in pairs:
            stack.append(pairs[ch])
        elif ch in pairs.values():
            if not stack or stack.pop() != ch:
                return f"unmatched {ch}"
    if stack:
        return f"unclosed delimiter expecting {stack[-1]}"
    mods = len(re.findall(r"\bmodule\b", clean))
    endmods = len(re.findall(r"\bendmodule\b", clean))
    if mods == 0 or mods != endmods:
        return f"module/endmodule mismatch: {mods} vs {endmods}"
    begins = len(re.findall(r"\bbegin\b", clean))
    ends = len(re.findall(r"\bend\b", clean))
    if begins != ends:
        return f"begin/end mismatch: {begins} vs {ends}"
    return None


def _is_cocotb_test_decorator(dec):
    if isinstance(dec, ast.Call):
        dec = dec.func
    return isinstance(dec, ast.Attribute) and dec.attr == "test" and isinstance(dec.value, ast.Name) and dec.value.id == "cocotb"


def _dut_attrs_in_func(node):
    attrs = set()
    calls = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name) and sub.value.id == "dut":
            if sub.attr not in IGNORED_COCOTB_ATTRS:
                attrs.add(sub.attr)
        elif isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
            if any(isinstance(arg, ast.Name) and arg.id == "dut" for arg in sub.args):
                calls.add(sub.func.id)
    return attrs, calls


def _extract_run_bindings(tree):
    bindings = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "run"):
            continue
        if not node.args or not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, str):
            continue
        top = node.args[0].value
        filt = None
        for kw in node.keywords:
            if kw.arg == "defines" and isinstance(kw.value, ast.Dict):
                for k, v in zip(kw.value.keys, kw.value.values):
                    if isinstance(k, ast.Constant) and k.value == "COCOTB_TEST_FILTER" and isinstance(v, ast.Constant):
                        filt = str(v.value)
        bindings.append((top, filt))
    return bindings


def extract_cocotb_dut_signals_by_top(text):
    tree = ast.parse(text)
    func_map = {}
    cocotb_tests = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_map[node.name] = _dut_attrs_in_func(node)
            if any(_is_cocotb_test_decorator(d) for d in node.decorator_list):
                cocotb_tests.append(node.name)

    def collect(fn_name, seen=None):
        seen = set() if seen is None else seen
        if fn_name in seen or fn_name not in func_map:
            return set()
        seen.add(fn_name)
        attrs, calls = func_map[fn_name]
        out = set(attrs)
        for callee in calls:
            out |= collect(callee, seen)
        return out

    bindings = _extract_run_bindings(tree)
    by_top = {}
    for top, filt in bindings:
        matched = [t for t in cocotb_tests if filt is None or re.search(filt, t)]
        assert matched, f"run({top!r}) filter {filt!r} matched no @cocotb.test() functions"
        sigs = by_top.setdefault(top, set())
        for t in matched:
            sigs |= collect(t)
    return by_top


def parse_sby_file(text):
    sections = {}
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip()
            sections.setdefault(current, [])
        elif current is not None:
            sections[current].append(line)
    return sections


def extract_sv_instantiations(text, module_names):
    clean = strip_sv_comments(text)
    found = []
    for mod in module_names:
        pattern = re.compile(rf"\b{re.escape(mod)}\b")
        pos = 0
        while True:
            m = pattern.search(clean, pos)
            if not m:
                break
            prefix = clean[max(0, m.start() - 12) : m.start()]
            if re.search(r"\bmodule\s+$", prefix):
                pos = m.end()
                continue
            idx = m.end()
            while idx < len(clean) and clean[idx].isspace():
                idx += 1
            if idx < len(clean) and clean[idx] == "#":
                idx += 1
                while idx < len(clean) and clean[idx].isspace():
                    idx += 1
                if idx < len(clean) and clean[idx] == "(":
                    idx = _matching_paren(clean, idx) + 1
            while idx < len(clean) and clean[idx].isspace():
                idx += 1
            inst_m = re.match(r"([A-Za-z_][A-Za-z0-9_$]*)\s*\(", clean[idx:])
            if not inst_m:
                pos = m.end()
                continue
            inst_name = inst_m.group(1)
            open_idx = idx + inst_m.end() - 1
            close_idx = _matching_paren(clean, open_idx)
            body = clean[open_idx + 1 : close_idx]
            ports = re.findall(r"\.([A-Za-z_][A-Za-z0-9_$]*)\s*\(", body)
            found.append((mod, inst_name, ports))
            pos = close_idx + 1
    return found


def _search_roots():
    roots = [ROOT]
    extra = os.environ.get("RTL_OVERLAY_ROOTS", "")
    for item in extra.split(os.pathsep):
        if item.strip():
            roots.append(Path(item.strip()))
    return roots


def _resolve_repo_file(rel_path):
    for root in _search_roots():
        cand = root / rel_path
        if cand.is_file():
            return cand
    return None


def test_parse_sv_modules_ansi_and_verilog2001():
    sv = """
    // header
    module demo_sv #(parameter int W = 8) (
      input logic clk,
      input logic rst_n,
      input logic signed [W-1:0] sample_in,
      output logic [3:0] dither_out
    );
    endmodule
    module demo_v #(parameter D = 8) (
      output [D-1:0] rdata,
      output wfull,
      input winc, wclk, wrst_n
    );
    endmodule
    """
    mods = parse_sv_modules(sv)
    assert mods["demo_sv"] == {"clk", "rst_n", "sample_in", "dither_out"}
    assert mods["demo_v"] == {"rdata", "wfull", "winc", "wclk", "wrst_n"}


def test_cocotb_port_checker_catches_typo():
    rtl = "module m(input logic clk, input logic rst_n, output logic y); endmodule\n"
    good_tb = """
import cocotb
from cocotb_run import run
@cocotb.test()
async def basic(dut):
    dut.clk.value = 0
    dut.rst_n.value = 1
    _ = dut.y.value
def test_m():
    run("m", ["m.sv"], __file__)
"""
    bad_tb = good_tb.replace("dut.y.value", "dut.y_typo.value")
    ports = parse_sv_modules(rtl)["m"]
    assert extract_cocotb_dut_signals_by_top(good_tb)["m"] <= ports
    assert not (extract_cocotb_dut_signals_by_top(bad_tb)["m"] <= ports)
    assert (extract_cocotb_dut_signals_by_top(bad_tb)["m"] - ports) == {"y_typo"}


def test_formal_sby_and_binding_checker_catches_bad_port():
    rtl = "module blk(input logic clk, input logic a, output logic y); endmodule\n"
    good_formal = "module f(input logic clk, a); logic y; blk dut (.clk(clk), .a(a), .y(y)); endmodule\n"
    bad_formal = "module f(input logic clk, a); logic y; blk dut (.clk(clk), .bad_pin(a), .y(y)); endmodule\n"
    ports = parse_sv_modules(rtl)["blk"]
    good_inst = extract_sv_instantiations(good_formal, ["blk"])
    assert len(good_inst) == 1 and set(good_inst[0][2]) == ports
    bad_inst = extract_sv_instantiations(bad_formal, ["blk"])
    assert set(bad_inst[0][2]) - ports == {"bad_pin"}


def test_existing_core_rtl_parsers_clean():
    for rel, mod, expected in [
        ("projects/fifo_bridge/design/async_fifo.sv", "async_fifo", {"w_clk", "w_rst_n", "w_en", "w_data", "w_full", "r_clk", "r_rst_n", "r_en", "r_data", "r_empty"}),
        ("projects/power_manager/design/dldo_ctrl.sv", "dldo_ctrl", {"clk", "rst_n", "lo", "hi", "far_lo", "far_hi", "on", "count", "drive"}),
    ]:
        path = ROOT / rel
        assert path.is_file()
        text = path.read_text()
        assert check_sv_balance(text) is None
        assert parse_sv_modules(text)[mod] == expected


def test_flagship_benches_syntax_and_sby_structure():
    for bench_rel, top_map in FLAGSHIP_COCOTB:
        bench_path = ROOT / bench_rel
        assert bench_path.is_file(), f"missing cocotb bench {bench_rel}"
        by_top = extract_cocotb_dut_signals_by_top(bench_path.read_text())
        assert set(by_top.keys()) == set(top_map.keys()), f"{bench_rel} tops {set(by_top)} != {set(top_map)}"
        for top, sigs in by_top.items():
            assert sigs, f"{bench_rel} accesses no dut signals for {top}"
    for sby_rel, formal_rel, _ in FLAGSHIP_FORMAL:
        sby_path = ROOT / sby_rel
        formal_path = ROOT / formal_rel
        assert sby_path.is_file(), f"missing sby {sby_rel}"
        assert formal_path.is_file(), f"missing formal sv {formal_rel}"
        formal_text = formal_path.read_text()
        assert check_sv_balance(formal_text) is None, f"{formal_rel}: {check_sv_balance(formal_text)}"
        formal_mods = set(parse_sv_modules(formal_text).keys())
        sections = parse_sby_file(sby_path.read_text())
        for req in ("tasks", "options", "engines", "script", "files"):
            assert sections.get(req), f"{sby_rel} missing [{req}]"
        file_basenames = {Path(f).name for f in sections["files"]}
        read_lines = [l for l in sections["script"] if "read " in l]
        assert read_lines, f"{sby_rel} has no read command"
        for rl in read_lines:
            tokens = [t for t in rl.split() if t.endswith((".sv", ".v"))]
            for tok in tokens:
                assert tok in file_basenames, f"{sby_rel} reads {tok} not listed in [files]"
        prep_tops = [m.group(1) for l in sections["script"] for m in [re.search(r"prep\b.*-top\s+([A-Za-z_][A-Za-z0-9_$]*)", l)] if m]
        assert prep_tops, f"{sby_rel} has no prep -top"
        for top in prep_tops:
            assert top in formal_mods, f"{sby_rel} prep -top {top} not found in {formal_rel}"


def test_flagship_cocotb_ports_match_rtl():
    resolved = {mod: _resolve_repo_file(rel) for _, m in FLAGSHIP_COCOTB for mod, rel in m.items()}
    if not any(resolved.values()) and not os.environ.get("RTL_OVERLAY_ROOTS"):
        pytest.skip("flagship RTL lives in stacked PRs #9, #10, #14; merge them or set RTL_OVERLAY_ROOTS")
    missing = [mod for mod, path in resolved.items() if path is None]
    assert not missing, f"missing flagship RTL modules: {missing}"
    for bench_rel, top_map in FLAGSHIP_COCOTB:
        by_top = extract_cocotb_dut_signals_by_top((ROOT / bench_rel).read_text())
        for mod, rtl_rel in top_map.items():
            rtl_text = resolved[mod].read_text()
            assert check_sv_balance(rtl_text) is None, f"{rtl_rel}: {check_sv_balance(rtl_text)}"
            rtl_ports = parse_sv_modules(rtl_text)[mod]
            used_ports = by_top[mod]
            unknown = used_ports - rtl_ports
            unused = rtl_ports - used_ports
            assert not unknown, f"{bench_rel} -> {mod}: unknown ports {sorted(unknown)} (valid: {sorted(rtl_ports)})"
            assert not unused, f"{bench_rel} -> {mod}: unexercised ports {sorted(unused)}"


def test_flagship_formal_bindings_match_rtl():
    resolved = {mod: _resolve_repo_file(rel) for _, _, m in FLAGSHIP_FORMAL for mod, rel in m.items()}
    if not any(resolved.values()) and not os.environ.get("RTL_OVERLAY_ROOTS"):
        pytest.skip("flagship RTL lives in stacked PRs #10, #14; merge them or set RTL_OVERLAY_ROOTS")
    missing = [mod for mod, path in resolved.items() if path is None]
    assert not missing, f"missing flagship formal RTL modules: {missing}"
    for sby_rel, formal_rel, mod_map in FLAGSHIP_FORMAL:
        sby_path = ROOT / sby_rel
        sections = parse_sby_file(sby_path.read_text())
        sby_dir_rel = Path(sby_rel).parent
        for rel_entry in sections["files"]:
            target_rel = os.path.normpath(str(sby_dir_rel / rel_entry))
            assert _resolve_repo_file(target_rel) is not None, f"{sby_rel} [files] entry missing: {rel_entry} -> {target_rel}"
        mod_ports = {}
        for mod, rtl_rel in mod_map.items():
            rtl_text = resolved[mod].read_text()
            assert check_sv_balance(rtl_text) is None, f"{rtl_rel}: {check_sv_balance(rtl_text)}"
            mod_ports[mod] = parse_sv_modules(rtl_text)[mod]
        formal_text = (ROOT / formal_rel).read_text()
        insts = extract_sv_instantiations(formal_text, list(mod_map.keys()))
        assert insts, f"{formal_rel} instantiates none of {sorted(mod_map)}"
        for mod, inst_name, bound_ports in insts:
            assert len(bound_ports) == len(set(bound_ports)), f"{formal_rel} {mod} {inst_name} has duplicate port bindings"
            unknown = set(bound_ports) - mod_ports[mod]
            missing_pins = mod_ports[mod] - set(bound_ports)
            assert not unknown, f"{formal_rel} {mod} {inst_name}: unknown pins {sorted(unknown)}"
            assert not missing_pins, f"{formal_rel} {mod} {inst_name}: unconnected pins {sorted(missing_pins)}"
