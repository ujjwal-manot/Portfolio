# Checks the power_manager result reader on made-up files: each level shifter corner must reach both rails within 5% of vin, switch within 2 ns both ways and draw under 1 nA from vin when settled, and a corner missing any number fails.
from power_results import shifter

def corner(tmp_path, name, **change):
    values = dict(lo_v=1e-7, hi_v=3.3, t_on_s=1e-10, t_off_s=5e-10, i_vin_on_a=-7e-12, i_vin_off_a=-7e-12, i_logic_a=-3e-11)
    values.update(change)
    path = tmp_path / f"shifter_{name}.txt"
    path.write_text("shifter " + " ".join(f"{k} {v}" for k, v in values.items()) + "\n")
    return path

def test_a_good_corner_passes(tmp_path):
    assert shifter([corner(tmp_path, "tt_27_3v3")]) == []

def test_each_limit_fails_its_corner(tmp_path):
    for change in (dict(lo_v=0.3), dict(hi_v=3.0), dict(t_on_s=3e-9), dict(t_off_s=2.5e-9), dict(i_vin_off_a=-2e-9)):
        assert len(shifter([corner(tmp_path, "ss_125_3v3", **change)])) == 1, change

def test_a_missing_number_fails(tmp_path):
    path = corner(tmp_path, "tt_27_3v3")
    path.write_text(path.read_text().replace(" hi_v 3.3", ""))
    assert shifter([path]) != []
