# Verifies compare_with_papers/jku_5t_ota SPICE netlists: exact JKU ota-5t transistor sizes (M1..M13) against published.json when present, IHP SG13G2 pin counts, subcircuit call matching, CACE bench metric coverage, and check_honesty rules.
import json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESIGN = HERE / "design" / "ota_5t.cir"
BENCH = HERE / "tests" / "cace_bench.cir"

EXPECTED_DEVICES = {
    "XM1": ("sg13_lv_nmos", "2u", "5u", "1", "1"),
    "XM2": ("sg13_lv_nmos", "2u", "5u", "1", "1"),
    "XM3": ("sg13_lv_pmos", "1.5u", "5u", "1", "1"),
    "XM4": ("sg13_lv_pmos", "1.5u", "5u", "1", "1"),
    "XM5": ("sg13_lv_nmos", "0.5u", "5u", "1", "1"),
    "XM6": ("sg13_lv_nmos", "2.5u", "5u", "5", "1"),
    "XM7": ("sg13_lv_nmos", "0.5u", "0.13u", "1", "1"),
    "XM8": ("sg13_lv_pmos", "1.5u", "0.13u", "1", "1"),
    "XM9": ("sg13_lv_nmos", "0.5u", "0.13u", "1", "1"),
    "XM10": ("sg13_lv_nmos", "0.5u", "0.13u", "1", "1"),
    "XM11": ("sg13_lv_pmos", "1.5u", "0.13u", "1", "1"),
    "XM12": ("sg13_lv_nmos", "0.5u", "0.13u", "1", "1"),
    "XM13": ("sg13_lv_pmos", "1.5u", "0.13u", "1", "1"),
}

def _parse_x_line(line):
    toks = line.split()
    params = {}
    pos = []
    for tok in toks[1:]:
        if "=" in tok:
            k, v = tok.split("=", 1)
            params[k.lower()] = v
        else:
            pos.append(tok)
    return toks[0], pos[:-1], pos[-1], params

def _um(val):
    return float(val.lower().rstrip("u"))

def test_jku_5t_ota_devices_match_published_sizes_and_pins():
    lines = DESIGN.read_text(encoding="utf-8").splitlines()
    sub = [l for l in lines if l.lower().startswith(".subckt ")]
    assert len(sub) == 1
    sub_toks = sub[0].split()
    assert sub_toks[1] == "ota_5t"
    assert sub_toks[2:] == ["vdd", "vout", "vinp", "vinn", "ibias_20u", "d_ena", "vss"]
    found = {}
    for line in lines[1:]:
        if line.startswith("X"):
            inst, nodes, model, params = _parse_x_line(line)
            assert len(nodes) == 4, f"{inst} must have 4 pins (d g s b), got {nodes}"
            found[inst] = (model, params["w"], params["l"], params["ng"], params["m"])
    assert found == EXPECTED_DEVICES
    pub = HERE.parent / "published.json"
    if pub.is_file():
        devs = json.loads(pub.read_text(encoding="utf-8"))["jku_5t_ota"]["devices"]
        for entry in devs:
            for name in entry["name"].split(","):
                model, w, l, ng, m = found["X" + name.strip()]
                assert model == entry["model"]
                assert abs(_um(w) - entry["w_um"]) < 1e-9
                assert abs(_um(l) - entry["l_um"]) < 1e-9
                assert int(ng) == entry["ng"]
                assert int(m) == entry["m"]

def test_cace_bench_instantiates_ota_and_measures_all_metrics():
    text = BENCH.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert ".include corner.inc" in lines
    assert ".include ota_5t.cir" in lines
    xota = [l for l in lines[1:] if l.startswith("XOTA ")]
    assert len(xota) == 1
    _, nodes, model, _ = _parse_x_line(xota[0])
    assert model == "ota_5t"
    assert len(nodes) == 7
    for metric in ("dc_gain", "bw_hz", "a0_db", "gbw_hz", "pm_deg", "cmrr_1k_db", "psrr_1k_db", "noise_rms"):
        assert metric in text

def test_spice_honesty_and_single_comment_rule():
    for path in (DESIGN, BENCH):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        assert lines[0].startswith("* ")
        assert "\u2014" not in text
        for idx, line in enumerate(lines[1:], start=2):
            assert not line.lstrip().startswith("*"), f"{path.name}:{idx} extra comment"
            assert not re.search(r"\s[;$]\s", line), f"{path.name}:{idx} inline comment"
            assert not re.match(r"\s*\.model\s+\S+\s+[np]mos", line, re.I), f"{path.name}:{idx} toy model"
