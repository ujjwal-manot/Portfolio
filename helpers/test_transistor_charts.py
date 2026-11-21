# Checks the chart reader on made-up square-law devices whose threshold and gm/Id points are known exactly, and that it splits NMOS and PMOS columns by length and drain voltage.
from transistor_charts import read, threshold, table

VT, K = 0.4, 2e-3

def linear(vds):
    rows = []
    for i in range(121):
        vgs = i / 100
        on = vgs > VT + vds / 2
        rows.append({"vgs": vgs, "ids": K * vds * (vgs - VT - vds / 2) if on else 1e-12, "gm": K * vds if on else 1e-12 * (1 + i / 1000)})
    return rows

def saturated():
    rows = []
    for i in range(1, 121):
        vgs = VT + i / 400
        rows.append({"vgs": vgs, "ids": K / 2 * (vgs - VT) ** 2, "gm": K * (vgs - VT)})
    return rows

def test_threshold_from_the_maximum_gm_line():
    assert abs(threshold(linear(0.05), 0.05) - VT) < 1e-9

def test_gm_over_id_points_land_where_square_law_puts_them():
    rows = {round(r["gm_id"]): r for r in table(saturated())}
    for g in (10, 16, 20):
        assert abs(rows[g]["vgs"] - (VT + 2 / g)) < 2e-4

def test_reader_splits_devices_lengths_and_drain_voltages(tmp_path):
    line = lambda vg, n, p: " ".join(map(str, [vg, *n, *p]))
    f = tmp_path / "charts_tt_27.txt"
    f.write_text("l 0.13u vds 0.05\n" + line(0.5, range(1, 10), range(11, 20)) + "\nl 2u vds 0.6\n" + line(0.6, range(21, 30), range(31, 40)) + "\n")
    data = read(f)
    assert sorted(data) == [("n", 1.3e-07, 0.05), ("n", 2e-06, 0.6), ("p", 1.3e-07, 0.05), ("p", 2e-06, 0.6)]
    assert data[("p", 2e-06, 0.6)][0] == {"vgs": 0.6, "ids": 31, "gm": 32, "gds": 33, "cgg": 34, "vth": 35, "vdss": 36, "fug": 37, "sid": 38, "sfl": 39}
