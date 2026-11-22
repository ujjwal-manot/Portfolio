# Tests sram_results.py on small hand-written hold tables.
from sram_results import held

GOOD = "case q_early_v q_late_v vdd_v\na 1.2 1.2 1.2\nb1 1.2 1.19 1.2\nb0 1e-4 2e-4 1.2\nc 1.2 1.2 1.2\nd 1.2 1.2 1.2\n"

def test_every_case_must_read_right_and_hold(tmp_path):
    path = tmp_path / "hold.txt"
    path.write_text(GOOD)
    assert held(path) == []
    path.write_text(GOOD.replace("b1 1.2 1.19 1.2", "b1 1.2 0.5 1.2"))
    assert held(path)
    path.write_text(GOOD.replace("b0 1e-4 2e-4 1.2", "b0 1.2 1.2 1.2"))
    assert held(path)
