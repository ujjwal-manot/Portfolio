# Checks same_values: two result files agree only when every named value is present, is not nan, and differs by no more than its stated tolerance.
from same_values import compare

def write(tmp_path, name, text):
    (tmp_path / name).write_text(text)
    return tmp_path / name

def test_values_within_tolerance_agree_and_others_do_not(tmp_path):
    a = write(tmp_path, "a.txt", "load settle_load_v 1e-6 kick_v 0.0600\n")
    assert compare({"settle_load_v": 2e-5, "kick_v": 1e-3}, a, write(tmp_path, "b.txt", "load settle_load_v 1.5e-5 kick_v 0.0605\n"))
    assert not compare({"settle_load_v": 2e-5, "kick_v": 1e-3}, a, write(tmp_path, "c.txt", "load settle_load_v 1e-6 kick_v 0.0620\n"))

def test_a_missing_or_nan_value_never_agrees(tmp_path):
    a = write(tmp_path, "a.txt", "load settle_load_v 1e-6 kick_v 0.06\n")
    assert not compare({"settle_load_v": 1.0}, a, write(tmp_path, "b.txt", "load settle_load_v nan kick_v 0.06\n"))
    assert not compare({"settle_load_v": 1.0}, a, write(tmp_path, "c.txt", "load kick_v 0.06\n"))
