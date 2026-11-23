# Fits the bandgap and LDO behavioral models (design/bandgap_model.cir, design/ldo_model.cir) from transistor measurements at tt 3.3 V 27 C only: the bandgap's vref(T) at code 8 as a least-squares quadratic about 27 C, its supply current as a straight line in T, the trim step and line slope as measured, vg as the measured drop below the supply, the start-up lag tau from the 10 ns ramp's settling (to 1% in ln(100) tau) and the turn-on supply from the 1 ms ramp's settling less that lag; the LDO's offset (vout less the bandgap's vref at no load), its own quiescent current (the total less the bandgap's at 27 C), and a two-pole loop (error amplifier pole f1, follower pole f2 = gp/Cout) solved from the measured no-load DC gain, crossover and phase margin, with Cout the measured MIM, the follower's square-law constant from gp and the measured bleed current, and the amplifier's 1 pF node scaled so gm R1 is the DC gain: python3 bandgap_ldo_model.py model_fit.txt dc_tt_3v3.txt ldo_tt_3v3_27.txt startup_tt_10n.txt startup_tt_1m.txt em_tt_3v3_27.txt > model_params.inc
import math, re, sys
from pathlib import Path

def poly(xs, ys, order):
    n = order + 1
    a = [[sum((x - 27) ** (i + j) for x in xs) for j in range(n)] + [sum(y * (x - 27) ** i for x, y in zip(xs, ys))] for i in range(n)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(a[r][i]))
        a[i], a[p] = a[p], a[i]
        for r in range(n):
            if r != i:
                f = a[r][i] / a[i][i]
                a[r] = [u - f * v for u, v in zip(a[r], a[i])]
    return [a[i][n] / a[i][i] for i in range(n)]

def poles(gain_db, fc, pm):
    a0, lag = 10 ** (gain_db / 20), math.radians(180 - pm)
    def mag(f2):
        f1 = fc / math.tan(lag - math.atan(fc / f2))
        return a0 / (math.hypot(1, fc / f1) * math.hypot(1, fc / f2)), f1
    lo = fc / math.tan(lag / 2)
    hi = fc / math.tan(lag - math.pi / 2) if lag > math.pi / 2 else fc * 1e9
    for _ in range(300):
        mid = math.sqrt(lo * hi)
        lo, hi = (mid, hi) if mag(mid)[0] > 1 else (lo, mid)
    return mag(lo)[1], lo

def fit(m):
    v0, a1, a2 = poly([t for t, _ in m["curve"]], [v for _, v in m["curve"]], 2)
    i0, i1 = poly([t for t, _ in m["ibg"]], [i for _, i in m["ibg"]], 1)
    tau = m["settle_10n_s"] / math.log(100)
    f1, f2 = poles(m["gain_db"], m["fc_hz"], m["pm_deg"])
    gp, c1 = 2 * math.pi * f2 * m["cout_f"], 1e-12
    r1 = 1 / (2 * math.pi * f1 * c1)
    return {"bg_v0": v0, "bg_a1": a1, "bg_a2": a2, "bg_step": m["step_v"], "bg_line": m["line_v_per_v"], "bg_i0": i0, "bg_i1": i1, "bg_vsg": m["vsg_v"],
            "bg_tau": tau, "bg_von": 3.3 * (m["ramp_1m_s"] + m["settle_1m_s"] - m["settle_10n_s"]) / m["ramp_1m_s"],
            "ld_off": m["vout_v"] - m["vref_v"], "ld_iq": m["iq_a"] - dict(m["ibg"])[27], "ld_ib": m["ibleed_a"], "ld_cout": m["cout_f"],
            "ld_k": gp ** 2 / (4 * m["ibleed_a"]), "ld_c1": c1, "ld_r1": r1, "ld_gm": 10 ** (m["gain_db"] / 20) / r1}

def values(path):
    out = {}
    for line in Path(path).read_text().splitlines():
        f = line.split()
        if f and f[0] != "*":
            out.update({f"{f[0]}.{k}": float(v) for k, v in zip(f[1::2], f[2::2])})
    return out

if __name__ == "__main__":
    fitbench, dc, ldo, s10n, s1m, em = sys.argv[1:]
    f, d, l, a, b = values(fitbench), values(dc), values(ldo), values(s10n), values(s1m)
    ibleed = float(re.search(r"^@n\.x2\.xbl\.\w+\[ids\]\s*=\s*(\S+)", Path(em).read_text(), re.M).group(1))
    lines = Path(fitbench).read_text().splitlines()
    m = {"curve": [(float(w[1]), float(w[2])) for w in (x.split() for x in lines) if w[0] == "curve"],
         "ibg": [(float(w[1]), float(w[2])) for w in (x.split() for x in lines) if w[0] == "ibg"],
         "vsg_v": f["fit.vsg_v"], "cout_f": f["fit.cout_f"], "step_v": d["dc.step_v"], "line_v_per_v": d["dc.line_v_per_v"],
         "settle_10n_s": a["startup.settle_s"], "settle_1m_s": b["startup.settle_s"], "ramp_1m_s": b["startup.ramp_s"],
         "gain_db": l["loop_0.gain_db"], "fc_hz": l["loop_0.fc_hz"], "pm_deg": l["loop_0.pm_deg"], "vout_v": l["ldo_dc.vout_v"],
         "vref_v": d["dc.untrimmed_v"], "iq_a": l["ldo_dc.iq_a"], "ibleed_a": ibleed}
    p = fit(m)
    if not all(math.isfinite(v) for v in p.values()):
        sys.exit("a fitted parameter is not a finite number")
    print(".param " + " ".join(f"{k}={v:.9g}" for k, v in p.items()))
