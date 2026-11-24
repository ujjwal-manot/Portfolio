# Tests dldo_results.py on small hand-written ngspice-style tables.
from dldo_results import cosim_check

def table(tmp_path, samples, n=4):
    rows = []
    for t, ins, count, drive, on in samples:
        bits = [1.2 * ((count >> i) & 1) for i in range(8)] + [1.2 * ((drive >> i) & 1) for i in range(8)] + [1.2 * (i < on) for i in range(n)]
        rows.append(" ".join(f"{t} {v}" for v in [1.2 * x for x in ins] + bits))
    path = tmp_path / "check.txt"
    path.write_text("\n".join(rows) + "\n")
    return path

def run(tmp_path, wrong=None):
    rst, flo, up = (0, 0, 0, 0, 0), (1, 0, 1, 0, 1), (1, 0, 0, 0, 1)
    states = [(0, 0, 0), (2, 3, 3), (4, 4, 4), (4, 4, 4)]
    if wrong:
        states[wrong[0]] = wrong[1]
    samples = [(0, rst, *states[0]), (9e-9, flo, *states[0]), (15e-9, flo, *states[1]), (29e-9, flo, *states[1]), (35e-9, up, *states[2]), (49e-9, up, *states[2]), (55e-9, up, *states[3])]
    return cosim_check(table(tmp_path, samples), n=4, big=2, p=1, pb=1, first=10e-9, period=20e-9)

def test_outputs_that_follow_the_rule_pass(tmp_path):
    problems, edges = run(tmp_path)
    assert problems == [] and edges == 3

def test_a_wrong_count_or_a_broken_thermometer_fails(tmp_path):
    assert run(tmp_path, (2, (4, 3, 3)))[0]
    assert run(tmp_path, (1, (2, 3, 1)))[0]
