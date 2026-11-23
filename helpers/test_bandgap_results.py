# Checks the bandgap result reader on made-up files: a corner fails on a trimmed tempco over 30 ppm/C, a trim code at either end of its range (the trim ran out) or a trimmed vref more than 0.75 of a trim step from 1.2063 V, Monte Carlo yield is counted trimmed and untrimmed with the spread of vref before and after trim and the codes used, and a start-up fails if vref ends away from 1.2063 V or never settles.
from bandgap_results import corners, montecarlo, startups

GOOD = "dc vref_v 1.2063 tc_ppm_per_c 11 vref_min_v 1.2042 vref_max_v 1.2064 supply_a 2.8e-05 line_v_per_v 1e-4 code 8 untrimmed_v 1.2063 untrimmed_tc_ppm_per_c 11 step_v 0.0031\n"

def write(tmp_path, name, text):
    (tmp_path / name).write_text(text)
    return tmp_path / name

def test_corner_fails_on_tempco_or_a_trim_at_its_end(tmp_path):
    a = write(tmp_path, "dc_tt_3v3.txt", GOOD)
    assert corners([a])[0]
    assert not corners([a, write(tmp_path, "dc_ss_3v0.txt", GOOD.replace("tc_ppm_per_c 11 ", "tc_ppm_per_c 31 "))])[0]
    assert not corners([a, write(tmp_path, "dc_ff_3v6.txt", GOOD.replace("code 8", "code 15"))])[0]
    assert not corners([a, write(tmp_path, "dc_fs_3v3.txt", GOOD.replace("code 8", "code 0"))])[0]

def test_corner_fails_when_the_trimmed_vref_misses_the_target(tmp_path):
    a = write(tmp_path, "dc_tt_3v3.txt", GOOD.replace("vref_v 1.2063 ", "vref_v 1.2085 "))
    assert corners([a])[0]
    assert not corners([write(tmp_path, "dc_sf_3v3.txt", GOOD.replace("vref_v 1.2063 ", "vref_v 1.2126 "))])[0]

def test_montecarlo_counts_trimmed_and_untrimmed_yield(tmp_path):
    runs = [write(tmp_path, f"mc_{i}.txt", GOOD.replace("untrimmed_tc_ppm_per_c 11", f"untrimmed_tc_ppm_per_c {40 if i < 10 else 11}").replace("code 8", f"code {6 + i % 5}")) for i in range(300)]
    r = montecarlo(runs)
    assert r["untrimmed_yield"] == 290 / 300 and r["trimmed_yield"] == 1.0 and r["codes"] == [6, 7, 8, 9, 10] and r["ok"]
    assert not montecarlo(runs[:200])["ok"], "200 of 200 bounds the yield at only 98.5%"
    runs[-1] = write(tmp_path, "mc_299.txt", GOOD.replace("tc_ppm_per_c 11 ", "tc_ppm_per_c 35 "))
    assert not montecarlo(runs)["ok"]

def test_startup_must_end_at_vref_and_settle(tmp_path):
    good = write(tmp_path, "startup_a.txt", "startup ramp_s 1e-08 final_v 1.20633 settle_s 7.5e-06\n")
    assert startups([good])[0]
    assert not startups([good, write(tmp_path, "startup_b.txt", "startup ramp_s 1e-03 final_v 0.002 settle_s -1\n")])[0]
    assert not startups([good, write(tmp_path, "startup_c.txt", "startup ramp_s 1e-03 final_v 1.2063 settle_s 2e-04\n")])[0]

def test_a_startup_written_as_nan_fails(tmp_path):
    good = write(tmp_path, "startup_a.txt", "startup ramp_s 1e-08 final_v 1.20633 settle_s 7.5e-06\n")
    assert not startups([good, write(tmp_path, "startup_n.txt", "startup ramp_s 1e-03 final_v nan settle_s 7.5e-06\n")])[0]
    assert not startups([good, write(tmp_path, "startup_m.txt", "startup ramp_s 1e-03 final_v 1.2063 settle_s nan\n")])[0]
