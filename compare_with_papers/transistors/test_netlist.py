# Verifies compare_with_papers/transistors/tests/ihp_spec.cir: exact SG13G2_os_process_spec.pdf Section 2.1/2.2 geometries (10/0.13, 10/10, 0.15/0.13 NMOS and PMOS) cross-checked against published.json when present, Vds = +-0.05 V and +-1.2 V sweeps, Vbs = 0 V, verified 4-pin IHP subcircuits, and check_honesty rules.
import json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC_CIR = HERE / "tests" / "ihp_spec.cir"

EXPECTED_DEVICES = {
    "XN10x013": ("sg13_lv_nmos", "10u", "0.13u"),
    "XN10x10": ("sg13_lv_nmos", "10u", "10u"),
    "XN015x013": ("sg13_lv_nmos", "0.15u", "0.13u"),
    "XP10x013": ("sg13_lv_pmos", "10u", "0.13u"),
    "XP10x10": ("sg13_lv_pmos", "10u", "10u"),
    "XP015x013": ("sg13_lv_pmos", "0.15u", "0.13u"),
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

def test_ihp_spec_geometries_and_bias_conditions():
    text = SPEC_CIR.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert ".include corner.inc" in lines
    found = {}
    for line in lines[1:]:
        if line.startswith("X"):
            inst, nodes, model, params = _parse_x_line(line)
            assert len(nodes) == 4, f"{inst} must have 4 pins (d g s b), got {nodes}"
            assert nodes[2] == "0" and nodes[3] == "0", f"{inst} must tie source and bulk to 0 (Vbs=0)"
            found[inst] = (model, params["w"], params["l"])
    assert found == EXPECTED_DEVICES
    assert "0.05" in text and "-0.05" in text
    assert "dc = 1.2" in text and "dc = -1.2" in text
    expected_params = (
        "VTN10x013", "VTN10x10", "VTN015x013", "IDSN013", "IOFFN013",
        "VTP10x013", "VTP10x10", "VTP015x013", "IDSP013", "IOFFP013",
    )
    for param in expected_params:
        assert param in text
    pub = HERE.parent / "published.json"
    if pub.is_file():
        spec = json.loads(pub.read_text(encoding="utf-8"))["sg13g2_process_spec"]
        pub_params = [e["parameter"] for grp in ("lv_nmos", "lv_pmos") for e in spec[grp]]
        assert set(pub_params) == set(expected_params)

def test_ihp_spec_honesty_and_single_comment():
    text = SPEC_CIR.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0].startswith("* ")
    assert "\u2014" not in text
    for idx, line in enumerate(lines[1:], start=2):
        assert not line.lstrip().startswith("*"), f"line {idx} extra comment"
        assert not re.search(r"\s[;$]\s", line), f"line {idx} inline comment"
        assert not re.match(r"\s*\.model\s+\S+\s+[np]mos", line, re.I), f"line {idx} toy model"
