# Sizes the folded-cascode two-stage Miller opamp from the typical-corner transistor charts and the chip.md spec by arithmetic alone, writes every width, length, finger count, capacitor and resistor as ngspice parameters, and prints what it predicts (gain, GBW, phase margin, slew, current) next to a plain two-stage Miller built from the same devices.
import math, sys
from transistor_charts import read

VDD, VCM, CL, RF, BETA = 1.2, 0.6, 2.05e-12, 20e3, 0.5
GBW_SPEC, GAIN_SPEC_DB, SR_SPEC, I_MAX = 20e6, 66, 10e6, 500e-6
GBW, P2_OVER_FC, UNIT, FINGER, MARGIN, VSB = 1.8 * GBW_SPEC, 3, 5e-6, 5e-6, 0.06, 0.25
RSH, REND, CAREA, CPERIM = 1360, 80e-6, 1.5e-15, 40e-18
CHOICE = {"in": ("n", 1e-6, 18), "tail": ("n", 2e-6, 14), "nsrc": ("n", 2e-6, 14), "nbot": ("n", 2e-6, 10), "ncas": ("n", 1e-6, 18),
          "psrc": ("p", 2e-6, 14), "pcas": ("p", 0.5e-6, 18), "out": ("p", 0.5e-6, 8)}

def at(rows, key, value):
    pair = next((a, b) for a, b in zip(rows, rows[1:]) if (a[key] - value) * (b[key] - value) <= 0)
    a, b = pair
    t = (value - a[key]) / (b[key] - a[key])
    return {k: a[k] + t * (b[k] - a[k]) for k in a}

def point(data, kind, current, vsb=0.0):
    d, l, g = CHOICE[kind]
    rows = [dict(r, gm_id=r["gm"] / r["ids"]) for r in data[(d, l, 0.6, vsb)]]
    rows = rows[max(range(len(rows)), key=lambda i: rows[i]["gm_id"]):]
    r = at(rows, "gm_id", g)
    w = current / (r["ids"] / FINGER)
    return {"dev": d, "l": l, "w": w, "cgg": r["cgg"] * w / FINGER, "gm": g * current, "gds": g * current / (r["gm"] / r["gds"]), "vgs": r["vgs"], "vdsat": r["vdss"], "i": current}

def diode_for(data, d, l, vgs):
    rows = [dict(r, gm_id=r["gm"] / r["ids"]) for r in data[(d, l, 0.6, 0.0)]]
    r = at(rows, "vgs", vgs)
    return UNIT / (r["ids"] / FINGER)

def resistor(r, w=1e-6):
    return w, (r - 2 * REND / w) / RSH * w

def mim(c):
    s = (-4 * CPERIM + math.sqrt(16 * CPERIM ** 2 + 4 * CAREA * c)) / (2 * CAREA)
    return s * 1e-6

def size(data):
    fc = BETA * GBW
    i_tail = 3 * UNIT
    m = {"in": point(data, "in", i_tail / 2), "tail": point(data, "tail", i_tail), "psrc": point(data, "psrc", i_tail),
         "pcas": point(data, "pcas", i_tail / 2, VSB), "ncas": point(data, "ncas", i_tail / 2, VSB), "nbot": point(data, "nbot", i_tail / 2)}
    i_out = UNIT
    while True:
        m["out"], m["sink"] = point(data, "out", i_out), point(data, "nsrc", i_out)
        gain2 = m["out"]["gm"] / (m["out"]["gds"] + m["sink"]["gds"] + 1 / RF)
        cc = m["in"]["gm"] / (2 * math.pi * GBW) * gain2 / (1 + gain2)
        load = CL + m["out"]["cgg"] * (1 + CL / cc)
        need = UNIT * math.ceil(2 * math.pi * P2_OVER_FC * fc * load / CHOICE["out"][2] / UNIT)
        if need <= i_out:
            break
        i_out = need
    rz = 1 / m["out"]["gm"]
    unit_n, unit_p = point(data, "nsrc", UNIT)["w"], point(data, "psrc", UNIT)["w"]
    n1 = (m["nbot"]["vdsat"] + m["nbot"]["vgs"] - m["ncas"]["vdsat"]) / 2
    vbnc = n1 + m["ncas"]["vgs"]
    vbpc = m["psrc"]["vdsat"] + MARGIN + m["pcas"]["vgs"]
    p = {"w_in": m["in"]["w"], "l_in": m["in"]["l"], "w_ncas": m["ncas"]["w"], "l_ncas": m["ncas"]["l"],
         "w_pcas": m["pcas"]["w"], "l_pcas": m["pcas"]["l"], "w_out": m["out"]["w"], "l_out": m["out"]["l"],
         "w_nu": unit_n, "l_nu": CHOICE["nsrc"][1], "w_pu": unit_p, "l_pu": CHOICE["psrc"][1],
         "m_tail": i_tail / UNIT, "m_fold": i_tail / UNIT, "w_bot": m["nbot"]["w"], "l_bot": m["nbot"]["l"], "m_sink": i_out / UNIT, "m_ref": 10e-6 / UNIT,
         "w_bnc": diode_for(data, "n", CHOICE["nsrc"][1], vbnc), "w_bpc": diode_for(data, "p", CHOICE["psrc"][1], vbpc)}
    p["w_cc"] = p["l_cc"] = mim(cc)
    p["w_rz"], p["l_rz"] = resistor(rz)
    r_up = m["pcas"]["gm"] / m["pcas"]["gds"] / (m["psrc"]["gds"] + m["in"]["gds"])
    r_down = m["ncas"]["gm"] / m["ncas"]["gds"] / m["nbot"]["gds"]
    folded = m["in"]["gm"] * r_up * r_down / (r_up + r_down) * gain2
    plain = m["in"]["gm"] / (m["in"]["gds"] + point(data, "psrc", i_tail / 2)["gds"]) * gain2
    p2 = m["out"]["gm"] / (2 * math.pi * load)
    supply = 10e-6 + 3 * UNIT + i_tail + 2 * i_tail + i_out
    predicted = {"gain_db": 20 * math.log10(folded), "plain_miller_gain_db": 20 * math.log10(plain), "gbw_hz": GBW,
                 "pm_deg": 90 - math.degrees(math.atan(fc / p2)), "slew_v_per_s": min(i_tail / cc, i_out / (CL + cc)),
                 "supply_a": supply, "gain2": gain2, "cc_f": cc, "rz_ohm": rz, "vbnc_v": vbnc, "vbpc_v": VDD - vbpc,
                 "o1_v": VDD - m["out"]["vgs"], "tail_headroom_v": VCM - m["in"]["vgs"] - m["tail"]["vdsat"],
                 "mirror_window_v": n1 - m["nbot"]["vdsat"], "pmos_stack_margin_v": m["out"]["vgs"] - m["psrc"]["vdsat"] - m["pcas"]["vdsat"],
                 "nmos_stack_margin_v": VDD - m["out"]["vgs"] - n1 - m["ncas"]["vdsat"]}
    return p, predicted

def resistor_rf():
    return resistor(RF)

if __name__ == "__main__":
    charts, out = sys.argv[1:]
    p, predicted = size(read(charts))
    p["w_rf"], p["l_rf"] = resistor_rf()
    p["w_cl"] = p["l_cl"] = mim(CL)
    p.update({"ng" + k[1:]: max(1, round(v / FINGER)) for k, v in list(p.items()) if k.startswith("w_") and k not in ("w_cc", "w_rz", "w_rf", "w_cl")})
    with open(out, "w") as f:
        for k, v in p.items():
            f.write(f".param {k}={v:.4g}\n")
    for k, v in predicted.items():
        print(f"predicted {k} {v:.4g}")
    for k, v in p.items():
        print(f"size {k} {v:.4g}")
    ok = predicted["gain_db"] >= GAIN_SPEC_DB and predicted["slew_v_per_s"] >= SR_SPEC and predicted["supply_a"] <= I_MAX and predicted["pm_deg"] >= 60
    print("prediction meets the spec" if ok else "prediction misses the spec")
    sys.exit(0 if ok else 1)
