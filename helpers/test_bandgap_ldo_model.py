# Checks the bandgap and LDO model fit: the quadratic and straight-line fits recover known coefficients, the two-pole solve recovers both poles from a loop's DC gain, crossover and phase margin, and fit() turns a set of tt measurements into the model parameters by the stated relations.
import cmath, math
import pytest
from bandgap_ldo_model import poly, poles, fit

def test_poly_recovers_a_quadratic_and_a_line():
    ts = list(range(-40, 130, 5))
    c = poly(ts, [1.2 + 1e-5 * (t - 27) - 2e-7 * (t - 27) ** 2 for t in ts], 2)
    assert c == pytest.approx([1.2, 1e-5, -2e-7], rel=1e-6)
    assert poly([-40, 27, 125], [3e-5 + 1e-7 * (t - 27) for t in (-40, 27, 125)], 1) == pytest.approx([3e-5, 1e-7], rel=1e-6)

def test_poles_recovers_a_two_pole_loop():
    a0, f1, f2 = 200.0, 20e3, 6e6
    t = lambda f: a0 / ((1 + 1j * f / f1) * (1 + 1j * f / f2))
    lo, hi = 1.0, 1e10
    for _ in range(200):
        mid = math.sqrt(lo * hi)
        lo, hi = (mid, hi) if abs(t(mid)) > 1 else (lo, mid)
    pm = 180 + math.degrees(cmath.phase(t(lo)))
    assert poles(20 * math.log10(a0), lo, pm) == pytest.approx((f1, f2), rel=1e-4)

def test_fit_follows_the_stated_relations():
    m = {"curve": [(t, 1.2 + 1e-5 * (t - 27)) for t in range(-40, 130, 5)], "ibg": [(-40, 2.8e-5), (27, 3.2e-5), (125, 3.8e-5)],
         "vsg_v": 1.1, "cout_f": 1e-10, "step_v": 3e-3, "line_v_per_v": 1e-4, "settle_10n_s": 2.3e-5, "settle_1m_s": -4.5e-4, "ramp_1m_s": 1e-3,
         "gain_db": 46.0, "fc_hz": 3.8e6, "pm_deg": 48.6, "vout_v": 1.2065, "vref_v": 1.2063, "iq_a": 1.77e-4, "ibleed_a": 1.1e-4}
    p = fit(m)
    assert p["bg_v0"] == pytest.approx(1.2) and p["bg_a1"] == pytest.approx(1e-5)
    assert p["bg_tau"] == pytest.approx(2.3e-5 / math.log(100))
    assert p["bg_von"] == pytest.approx(3.3 * (1e-3 - 4.5e-4 - 2.3e-5) / 1e-3)
    assert p["ld_off"] == pytest.approx(2e-4)
    assert p["ld_iq"] == pytest.approx(1.77e-4 - 3.2e-5)
    f1, f2 = poles(46.0, 3.8e6, 48.6)
    assert p["ld_k"] == pytest.approx((2 * math.pi * f2 * 1e-10) ** 2 / (4 * 1.1e-4))
    assert p["ld_gm"] * p["ld_r1"] == pytest.approx(10 ** (46 / 20))
    assert 1 / (2 * math.pi * p["ld_r1"] * p["ld_c1"]) == pytest.approx(f1)
