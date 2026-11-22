# Reads power_manager results: level shifter corners (shifter_<corner>.txt from tests/shifter.cir) must reach both rails within 5% of vin, switch within 2 ns both ways (a tenth of the controller's 20 ns clock) and draw under 1 nA from vin once settled.
import sys
from pathlib import Path

def values(path):
    words = Path(path).read_text().split()[1:]
    return {words[i]: float(words[i + 1]) for i in range(0, len(words) - 1, 2)}

def shifter(paths):
    fails = []
    for path in paths:
        v, name = values(path), Path(path).stem
        need = ("lo_v", "hi_v", "t_on_s", "t_off_s", "i_vin_on_a", "i_vin_off_a")
        if any(k not in v for k in need):
            fails.append(f"{name}: missing {[k for k in need if k not in v]}")
            continue
        vin = float(name.split("_")[-1].replace("v", "."))
        checks = [(v["lo_v"] <= 0.05 * vin, f"low level {v['lo_v']:.3g} V"), (v["hi_v"] >= 0.95 * vin, f"high level {v['hi_v']:.3g} V"),
                  (max(v["t_on_s"], v["t_off_s"]) <= 2e-9, f"delay {max(v['t_on_s'], v['t_off_s']):.3g} s"),
                  (max(abs(v["i_vin_on_a"]), abs(v["i_vin_off_a"])) <= 1e-9, f"static current {max(abs(v['i_vin_on_a']), abs(v['i_vin_off_a'])):.3g} A")]
        fails += [f"{name}: {why}" for ok, why in checks if not ok]
    return fails

if __name__ == "__main__":
    mode, paths = sys.argv[1], sys.argv[2:]
    if mode == "shifter":
        for p in paths:
            v = values(p)
            print(f"{Path(p).stem}: low {v.get('lo_v', float('nan')):.3g} V, high {v.get('hi_v', float('nan')):.3g} V, on {v.get('t_on_s', float('nan')) * 1e12:.0f} ps, off {v.get('t_off_s', float('nan')) * 1e12:.0f} ps, vin current {max(abs(v.get('i_vin_on_a', 0)), abs(v.get('i_vin_off_a', 0))):.3g} A")
        fails = shifter(paths)
    for f in fails:
        print("FAIL " + f)
    print("every check passes" if not fails else f"{len(fails)} failures")
    sys.exit(1 if fails else 0)
