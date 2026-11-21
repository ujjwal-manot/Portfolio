# Prints the signoff numbers of a LibreLane run (power and IR drop marked as vectorless estimates) from its final metrics.json and fails on any DRC, LVS, antenna, slew, capacitance or fanout violation or any negative setup or hold slack: python3 metrics.py runs/<tag>/final/metrics.json.
import json, sys

COUNTS = ["magic__drc_error__count", "klayout__drc_error__count", "route__drc_errors", "design__lvs_error__count", "antenna__violating__nets",
          "design__max_slew_violation__count", "design__max_cap_violation__count", "design__max_fanout_violation__count"]
SHOWN = ["design__die__area", "design__core__area", "design__instance__utilization", "design__instance__count__stdcell", "design__instance__count__class:sequential_cell",
         "design__instance__count__class:clock_buffer", "design__instance__count__class:timing_repair_buffer", "route__wirelength"]
VECTORLESS = ["power__total", "ir__drop__worst"]
CORNERS = ["nom_slow_1p08V_125C", "nom_typ_1p20V_25C", "nom_fast_1p32V_m40C"]

def check(m):
    bad = [k for k in COUNTS if m[k] != 0]
    for c in CORNERS:
        bad += [f"{k} at {c}" for k in ("timing__setup__ws", "timing__hold__ws") if m[f"{k}__corner:{c}"] < 0]
    return bad

if __name__ == "__main__":
    m = json.load(open(sys.argv[1]))
    for k in COUNTS:
        print(f"{k:50} {m[k]}")
    for k in SHOWN:
        print(f"{k:50} {m[k]:.6g}")
    for k in VECTORLESS:
        print(f"{k:50} {m[k]:.6g} (vectorless: LibreLane's default switching activity, not the simulated traffic)")
    for c in CORNERS:
        print(f"{c:22} setup slack {m[f'timing__setup__ws__corner:{c}']:.4f} ns, hold slack {m[f'timing__hold__ws__corner:{c}']:.4f} ns, clock skew {m[f'clock__skew__worst_setup__corner:{c}']:.4f} ns")
    bad = check(m)
    print("FAIL " + ", ".join(bad) if bad else "layout clean: no DRC, LVS, antenna or electrical violation, no negative slack")
    sys.exit(1 if bad else 0)
