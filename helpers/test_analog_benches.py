# Verifies SPICE subcircuit-port consistency, verified IHP SG13G2 PDK pin counts, zero toy .model lines, single-comment honesty, broken-patch application, KLayout/Magic layout script net/port/CDL consistency, and phase_noise/eye_diagram bench contracts.
import os, re, runpy, subprocess, sys, types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PDK_SUBCKT_PINS = {
    "sg13_lv_nmos": 4,
    "sg13_lv_pmos": 4,
    "sg13_hv_nmos": 4,
    "sg13_hv_pmos": 4,
    "npn13g2": 4,
    "pnpmpa": 3,
    "sg13_hv_svaricap": 4,
    "cap_cmim": 2,
    "rppd": 3,
    "rhigh": 3,
    "rsil": 3,
    "bondpad": 1,
    "diodevdd_2kv": 3,
    "diodevss_2kv": 3,
}

EXPECTED_DUT_PINS = {
    "ota_5t": 7,
    "lc_vco": 10,
    "lc_vco_hbt": 10,
    "ctle": 7,
    "cml_tx_ffe": 11,
    "sampler": 7,
    "cp_lf": 6,
}

TARGET_DIRS = (
    ROOT / "compare_with_papers" / "jku_5t_ota",
    ROOT / "compare_with_papers" / "transistors",
    ROOT / "projects" / "lc_vco",
    ROOT / "projects" / "serdes_frontend",
    ROOT / "projects" / "frac_n_pll",
)

LAYOUT_TARGETS = (
    (ROOT / "projects" / "frac_n_pll", "cp_lf"),
    (ROOT / "projects" / "lc_vco", "lc_vco"),
    (ROOT / "projects" / "serdes_frontend", "ctle"),
)

def _logical_lines(text):
    merged = []
    for raw in text.splitlines():
        if raw.startswith("+") and merged:
            merged[-1] = merged[-1] + " " + raw[1:].strip()
        else:
            merged.append(raw)
    return merged

def _parse_spice_file(path):
    lines = _logical_lines(path.read_text(encoding="utf-8"))
    subckts = {}
    calls = []
    in_control = False
    for idx, line in enumerate(lines[1:], start=2):
        stripped = line.strip()
        low = stripped.lower()
        if low.startswith(".control"):
            in_control = True
            continue
        if low.startswith(".endc"):
            in_control = False
            continue
        if in_control or not stripped:
            continue
        if low.startswith(".subckt "):
            toks = stripped.split()
            name = toks[1].lower()
            pins = [t for t in toks[2:] if "=" not in t]
            subckts[name] = len(pins)
        elif stripped[0] in ("X", "x"):
            toks = stripped.split()
            pos = [t for t in toks[1:] if "=" not in t]
            assert len(pos) >= 2, f"{path}:{idx} malformed X call: {stripped}"
            calls.append((idx, toks[0], pos[-1].lower(), pos[:-1]))
    return subckts, calls

def _all_target_cir_files():
    found = []
    for folder in TARGET_DIRS:
        if folder.is_dir():
            found.extend(sorted(folder.rglob("*.cir")))
    return found

def _install_pya_stub():
    class DBox:
        def __init__(self, x0=0.0, y0=0.0, x1=1.0, y1=1.0):
            self.left, self.bottom, self.right, self.top = float(x0), float(y0), float(x1), float(y1)
        def width(self):
            return self.right - self.left
        def height(self):
            return self.top - self.bottom
        def center(self):
            return types.SimpleNamespace(x=0.5 * (self.left + self.right), y=0.5 * (self.bottom + self.top))
        def transformed(self, tr):
            return self
        def moved(self, dx, dy):
            return DBox(self.left + dx, self.bottom + dy, self.right + dx, self.top + dy)

    class DTrans:
        def __init__(self, x=0.0, y=0.0):
            self.x, self.y = float(x), float(y)

    class DText:
        def __init__(self, text, tr):
            self.text, self.tr = text, tr

    class DCellInstArray:
        def __init__(self, idx, tr):
            self.idx, self.tr = idx, tr

    class Shapes:
        def __init__(self):
            self.items = []
        def insert(self, obj):
            self.items.append(obj)

    class Cell:
        def __init__(self, name, params=None):
            self.name = name
            self.params = params or {}
            self._shapes = {}
        def cell_index(self):
            return 1
        def shapes(self, li):
            return self._shapes.setdefault(li, Shapes())
        def insert(self, inst):
            pass
        def dbbox(self):
            return DBox(0.0, 0.0, 4.0, 4.0)
        def begin_shapes_rec(self, li):
            ng = int(self.params.get("ng", "1"))
            boxes = [DBox(0.5 * i, 0.0, 0.5 * i + 0.2, 1.0) for i in range(max(2, ng + 1))]
            items = [types.SimpleNamespace(shape=lambda b=b: types.SimpleNamespace(dbbox=lambda: b), dtrans=lambda: DTrans()) for b in boxes]
            return types.SimpleNamespace(each=lambda: items)
        def write(self, path):
            Path(path).write_bytes(b"GDSII_STUB")

    class Layout:
        def __init__(self):
            self.dbu = 0.001
            self.technology_name = ""
            self._layers = {}
        def create_cell(self, name, *args):
            params = args[1] if len(args) >= 2 and isinstance(args[1], dict) else {}
            return Cell(name, params)
        def layer(self, num, dt):
            return self._layers.setdefault((num, dt), len(self._layers) + 1)

    sys.modules["pya"] = types.SimpleNamespace(
        Layout=Layout, DBox=DBox, DTrans=DTrans, DText=DText, DCellInstArray=DCellInstArray
    )
    sys.modules["sg13g2_pycell_lib"] = types.SimpleNamespace()
    os.environ.setdefault("PDK_ROOT", "/foss/pdks")

def test_all_required_benches_exist():
    required = (
        ROOT / "compare_with_papers" / "jku_5t_ota" / "design" / "ota_5t.cir",
        ROOT / "compare_with_papers" / "jku_5t_ota" / "tests" / "cace_bench.cir",
        ROOT / "compare_with_papers" / "transistors" / "tests" / "ihp_spec.cir",
        ROOT / "projects" / "lc_vco" / "tests" / "osc_tran.cir",
        ROOT / "projects" / "lc_vco" / "tests" / "band_sweep.cir",
        ROOT / "projects" / "serdes_frontend" / "tests" / "ctle_ac.cir",
        ROOT / "projects" / "serdes_frontend" / "tests" / "tx_eye.cir",
        ROOT / "projects" / "serdes_frontend" / "tests" / "s11_ac.cir",
        ROOT / "projects" / "serdes_frontend" / "tests" / "sampler_tran.cir",
        ROOT / "projects" / "frac_n_pll" / "design" / "cp_lf.cir",
        ROOT / "projects" / "frac_n_pll" / "design" / "cp_lf_sizes.inc",
        ROOT / "projects" / "frac_n_pll" / "broken" / "cp_mismatch_20pct.patch",
        ROOT / "projects" / "frac_n_pll" / "broken" / "lf_zero_removed.patch",
        ROOT / "projects" / "frac_n_pll" / "layout" / "cp_lf.py",
        ROOT / "projects" / "frac_n_pll" / "layout" / "extract.tcl",
    )
    for path in required:
        assert path.is_file(), f"missing SPICE/layout/patch file: {path}"

def test_every_x_call_matches_subckt_pin_count():
    cir_files = _all_target_cir_files()
    assert len(cir_files) >= 10
    defined = {}
    parsed = {}
    for path in cir_files:
        subckts, calls = _parse_spice_file(path)
        parsed[path] = calls
        for name, count in subckts.items():
            if name in EXPECTED_DUT_PINS:
                assert count == EXPECTED_DUT_PINS[name], f"{path} .subckt {name} has {count} pins, expected {EXPECTED_DUT_PINS[name]}"
            defined[name] = count
    known = {**PDK_SUBCKT_PINS, **EXPECTED_DUT_PINS, **defined}
    total_calls = 0
    for path, calls in parsed.items():
        for idx, inst, model, pins in calls:
            assert model in known, f"{path}:{idx} {inst} references unverified subckt '{model}'"
            assert len(pins) == known[model], f"{path}:{idx} {inst} calls {model} with {len(pins)} pins, expected {known[model]}"
            total_calls += 1
    assert total_calls >= 35

def test_zero_toy_models_and_strict_honesty_across_analog_benches():
    for path in _all_target_cir_files():
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        assert lines[0].startswith("* "), f"{path} line 1 must start with '* '"
        assert "\u2014" not in text, f"{path} contains em dash"
        for idx, line in enumerate(lines[1:], start=2):
            assert not line.lstrip().startswith("*"), f"{path}:{idx} extra comment line"
            assert not re.search(r"\s[;$]\s", line), f"{path}:{idx} inline comment token"
            assert not re.match(r"\s*\.model\s+\S+\s+[np]mos", line, re.I), f"{path}:{idx} toy .model line"
        if path.parent.name == "tests":
            assert ".include corner.inc" in lines, f"{path} must include corner.inc"
            assert lines[-1].strip().lower() == ".end", f"{path} must end with .end"

def test_flagship_benches_and_broken_patches():
    osc = (ROOT / "projects" / "lc_vco" / "tests" / "osc_tran.cir").read_text(encoding="utf-8")
    assert "set wr_singlescale" in osc
    assert "unset wr_vecnames" in osc
    assert "wrdata vco_wave.txt vdiff" in osc
    assert "trnoise(" in osc
    band = (ROOT / "projects" / "lc_vco" / "tests" / "band_sweep.cir").read_text(encoding="utf-8")
    assert "while code < 16" in band
    assert "foreach vt_frac 0 1" in band
    ctle = (ROOT / "projects" / "serdes_frontend" / "tests" / "ctle_ac.cir").read_text(encoding="utf-8")
    assert "at=5g" in ctle
    assert "ctle_ac.txt" in ctle
    eye = (ROOT / "projects" / "serdes_frontend" / "tests" / "tx_eye.cir").read_text(encoding="utf-8")
    assert "set wr_singlescale" in eye
    assert "unset wr_vecnames" in eye
    assert "wrdata tx_eye_wave.txt vrx_diff" in eye
    assert "td=100p" in eye and "td=200p" in eye
    s11 = (ROOT / "projects" / "serdes_frontend" / "tests" / "s11_ac.cir").read_text(encoding="utf-8")
    assert "at=5g" in s11
    assert "s11_ac.txt" in s11
    smp = (ROOT / "projects" / "serdes_frontend" / "tests" / "sampler_tran.cir").read_text(encoding="utf-8")
    assert "sampler_tran.txt" in smp
    for folder in TARGET_DIRS:
        broken_dir = folder / "broken"
        if broken_dir.is_dir():
            for patch in sorted(broken_dir.glob("*.patch")):
                res = subprocess.run(["git", "apply", "--check", str(patch)], cwd=folder, capture_output=True, text=True)
                assert res.returncode == 0, f"{patch} failed git apply --check: {res.stderr}"

def test_layout_scripts_and_extract_tcl_match_netlists(tmp_path):
    _install_pya_stub()
    checked = 0
    for proj_dir, cell in LAYOUT_TARGETS:
        py_path = proj_dir / "layout" / f"{cell}.py"
        tcl_path = proj_dir / "layout" / "extract.tcl"
        cir_path = proj_dir / "design" / f"{cell}.cir"
        sizes_path = proj_dir / "design" / f"{cell}_sizes.inc"
        if not py_path.is_file():
            continue
        assert tcl_path.is_file() and cir_path.is_file() and sizes_path.is_file()
        tcl_text = tcl_path.read_text(encoding="utf-8")
        assert f"gds read {cell}.gds" in tcl_text
        assert f"load {cell}" in tcl_text
        assert f"cellname rename {cell} {cell}_pex" in tcl_text
        assert f"ext2spice -o {cell}_pex.spice" in tcl_text
        out_dir = tmp_path / cell
        os.environ["SIZES"] = str(sizes_path)
        os.environ["OUT"] = str(out_dir)
        ns = runpy.run_path(str(py_path))
        assert (out_dir / f"{cell}.gds").is_file()
        cdl_file = out_dir / f"{cell}.cdl"
        assert cdl_file.is_file()
        cdl_text = cdl_file.read_text(encoding="utf-8")
        assert "{" not in cdl_text and "}" not in cdl_text
        assert "mm_ok" not in cdl_text
        cir_sub = [l for l in cir_path.read_text(encoding="utf-8").splitlines() if l.lower().startswith(f".subckt {cell} ")][0]
        ports = set(cir_sub.split()[2:])
        assert ports <= set(ns["nets"]), f"{cell}.py nets missing ports: {ports - set(ns['nets'])}"
        checked += 1
    assert checked >= 1
