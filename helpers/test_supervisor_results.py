# Checks the supervisor result reader: detector codes count reached taps and flag bubbles, saturation, a code that falls as vdd_cpu rises, a missing or non-numeric point; supervisor runs give the four trip points from the right phases, fail a trip outside its limit, a chattering comparator, a reset released below a floor and a run that stopped early; Monte Carlo yield comes with its one-sided 95% lower bound.
import math
from supervisor_results import decode, detector, trips, supervisor, montecarlo, VIN_FALL, MEM_FALL

def taps(code, bubble=None, vmem=1.2):
    return [vmem * ((k % 2 == 0) == (k <= code and k != bubble)) for k in range(1, 65)]

def det_file(tmp_path, codes, name="detector_tt_25.txt"):
    vdds = [0.8 + 0.05 * i for i in range(10)]
    path = tmp_path / name
    path.write_text("".join(" ".join(str(x) for x in [v] + taps(c)) + "\n" for v, c in zip(vdds, codes)))
    return path

def test_decode_counts_taps_and_bubbles():
    assert decode(taps(30)) == (30, 0)
    assert decode(taps(30, bubble=12)) == (29, 1)
    assert decode(taps(0)) == (0, 0)

def test_detector_passes_a_clean_rising_sweep(tmp_path):
    ok, lines = detector([det_file(tmp_path, list(range(10, 60, 5)))])
    assert ok, lines

def test_detector_fails_saturation_fall_and_gaps(tmp_path):
    assert not detector([det_file(tmp_path, list(range(20, 70, 5)))])[0]
    codes = list(range(10, 60, 5))
    codes[5] = codes[4] - 2
    assert not detector([det_file(tmp_path, codes)])[0]
    path = det_file(tmp_path, list(range(10, 60, 5)))
    path.write_text("\n".join(path.read_text().splitlines()[:-1]) + "\n")
    assert not detector([path])[0]
    path.write_text(path.read_text().replace("1.2", "nan", 1))
    assert not detector([path])[0]

def sup_rows(vin_fall=2.894, vin_rise=2.944, mem_fall=1.106, mem_rise=1.126, ramp=100e-6, chatter=False, early=False, release=None):
    t0, rows, t = ramp + 150e-6, [], 0.0
    end = t0 + 2300e-6
    while t <= end + 1e-12:
        vin = 3.3 * t / ramp if t < ramp else 3.3 if t < t0 else 3.3 - (t - t0) / 1e-3 if t < t0 + 600e-6 else 2.7 + (t - t0 - 600e-6) / 1e-3 if t < t0 + 1200e-6 else 3.3
        mem = 0 if t < ramp + 20e-6 else min(1.2, 1.2 * (t - ramp - 20e-6) / 50e-6) if t < t0 else 1.2 if t < t0 + 1250e-6 else 1.2 - 0.3 * (t - t0 - 1250e-6) / 1e-3 if t < t0 + 1750e-6 else 1.05 + 0.3 * (t - t0 - 1750e-6) / 1e-3 if t < t0 + 2250e-6 else 1.2
        falling_in = t < t0 + 600e-6
        vok = vin > (vin_fall if t >= t0 and falling_in else vin_rise)
        if chatter and t0 + 100e-6 < t < t0 + 110e-6:
            vok = not vok
        mok = mem > (mem_fall if t0 + 1250e-6 <= t < t0 + 1750e-6 else mem_rise)
        rst = mem if (vok and mok) or (release is not None and vin > release and t < t0) else 0.0
        rows.append((t, vin, mem, 3.3 * vok, 3.3 * mok, rst, 1.206, -4e-5))
        t += 1e-6
    if early:
        rows = rows[: len(rows) // 2]
    return rows, end

def write(tmp_path, rows, name="sup_tt_27_100u.txt"):
    path = tmp_path / name
    path.write_text("".join(" ".join(f"{r[0]} {v}" for v in r[1:]) + "\n" for r in rows))
    return path

def test_trips_come_from_their_phases():
    rows, end = sup_rows()
    got = trips(rows, 100e-6)
    assert abs(got["vin_fall"] - 2.894) < 2e-3 and abs(got["vin_rise"] - 2.944) < 2e-3
    assert abs(got["mem_fall"] - 1.106) < 1e-3 and abs(got["mem_rise"] - 1.126) < 1e-3

def test_supervisor_passes_the_design_and_fails_each_fault(tmp_path):
    assert supervisor([write(tmp_path, sup_rows()[0])])[0]
    assert not supervisor([write(tmp_path, sup_rows(vin_fall=2.994, vin_rise=3.044)[0])])[0]
    assert not supervisor([write(tmp_path, sup_rows(mem_fall=1.006, mem_rise=1.026)[0])])[0]
    assert not supervisor([write(tmp_path, sup_rows(chatter=True)[0])])[0]
    assert not supervisor([write(tmp_path, sup_rows(early=True)[0])])[0]
    assert not supervisor([write(tmp_path, sup_rows(release=2.0)[0])])[0]

def test_limits_are_the_written_ones():
    assert VIN_FALL == (2.80, 3.00) and MEM_FALL == (1.08, 1.14)

def test_montecarlo_yield_and_bound(tmp_path):
    good = [write(tmp_path, sup_rows()[0], f"sup_mc_{n}.txt") for n in range(3)]
    bad = write(tmp_path, sup_rows(vin_fall=2.994, vin_rise=3.044)[0], "sup_mc_9.txt")
    ok, lines = montecarlo(good)
    assert ok and any("lower bound" in l and f"{0.05 ** (1 / 3):.1%}" in l for l in lines), lines
    assert not montecarlo(good + [bad])[0]
