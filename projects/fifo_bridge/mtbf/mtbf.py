# Fits the metastability time constant from the ngspice flop sweeps where the solver still resolves the gap (tt 27 C, ss 125 C, ss -40 C as sc, since at 1.08 V cold is the slower side, and ff -40 C), compares each flip point with the IHP liberty setup time (sc against the 125 C slow library, IHP ships no cold one), checks sync2.sv uses the measured capture window, and works out the bridge synchronizers' MTBF.
import math, re, statistics, sys
from pathlib import Path

LIB = "/foss/pdks/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_{}.lib"
CORNERS = {"tt": "typ_1p20V_25C", "ss": "slow_1p08V_125C", "sc": "slow_1p08V_125C", "ff": "fast_1p32V_m40C"}
CROSSINGS = [("w_gray into m_clk", 50e6, 10e6), ("r_gray into s_clk", 10e6, 50e6)]
SYNC2 = Path(__file__).resolve().parents[1] / "design" / "sync2.sv"

def setup(corner):
    s = Path(LIB.format(CORNERS[corner])).read_text()
    cell = s[s.index("cell (sg13g2_dfrbpq_1)"):]
    pin = cell[cell.index("pin (D)"):cell.index("\n  cell (")]
    t = next(x for x in pin.split("timing ()")[1:] if "setup_rising" in x)
    return max(float(re.search(k + r'.*?values \(\W*([-\d.]+)', t, re.S).group(1)) for k in ("rise_constraint", "fall_constraint")) * 1e-9

def fit(rows):
    ok = [r for i, r in enumerate(rows) if all(rows[k + 1][1] > rows[k][1] for k in range(i + 1))]
    slope = [(b[1] - a[1]) / math.log(a[0] / b[0]) for a, b in zip(ok, ok[1:])]
    runs = [(j - i, i, j) for i in range(len(slope)) for j in range(i + 4, len(slope) + 1)
            if all(abs(s / statistics.median(slope[i:j]) - 1) < 0.15 for s in slope[i:j])]
    if not runs:
        raise SystemExit("no stretch of four steps follows the log law")
    _, i, j = max(runs, key=lambda r: (r[0], -r[1]))
    x, y = [math.log(g) for g, _ in ok[i:j + 1]], [s for _, s in ok[i:j + 1]]
    mx, my = statistics.mean(x), statistics.mean(y)
    b = sum((u - mx) * (v - my) for u, v in zip(x, y)) / sum((u - mx) ** 2 for u in x)
    a = my - b * mx
    return -b, a, ok[i][0], ok[j][0], max(abs(v - a - b * u) for u, v in zip(x, y)), ok[-1][0]

offsets, worst = [], None
for path in sys.argv[1:]:
    name = Path(path).stem.removeprefix("mtbf_")
    corner = name.split("_")[0]
    rows = [[float(v) for v in line.split()] for line in Path(path).read_text().splitlines()[1:]]
    if len(rows) != 72:
        raise SystemExit(f"{name}: {len(rows)} sweep rows, expected 72")
    capture = [(g, tq - tc) for side, g, tq, tc, td in rows if side == 0]
    if any(s <= 0 for _, s in capture) or any(tq > tc for side, g, tq, tc, td in rows if side == 1):
        raise SystemExit(f"{name}: capture side missed or miss side moved after the clock, so the flip point is wrong or the window is two-sided")
    offset = statistics.mean(tc - td - g * (1 - 2 * side) for side, g, tq, tc, td in rows)
    offsets.append(offset)
    tau, a, g_hi, g_lo, resid, floor = fit(capture)
    lib = setup(corner)
    ln_rate = []
    for label, fc, fd in CROSSINGS:
        ln_rate.append((a - (1 / fc - lib)) / tau + math.log(fc * fd))
    top = max(ln_rate)
    years = -(top + math.log(sum(math.exp(r - top) for r in ln_rate))) / math.log(10) - math.log10(3.156e7)
    print(f"{name}: tau {tau * 1e12:.1f} ps (fit {g_hi:.2e} to {g_lo:.2e} s gap, worst residual {resid * 1e12:.2f} ps, solver floor below {floor:.2e} s),"
          f" flip {offset * 1e12:.1f} ps before CLK (liberty setup {lib * 1e12:.1f} ps), bridge MTBF 10^{years:.0f} years")
    worst = years if worst is None else min(worst, years)

keep, take = math.floor(min(offsets) * 1e13) / 1e4, math.ceil(max(offsets) * 1e13) / 1e4
print(f"capture window: data older than {take} ns is taken, younger than {keep} ns is missed, between is either; worst bridge MTBF 10^{worst:.0f} years")
used = dict(re.findall(r"(KEEP|TAKE) = ([\d.]+)", SYNC2.read_text()))
if used != {"KEEP": str(keep), "TAKE": str(take)}:
    raise SystemExit(f"sync2.sv uses {used}, but the sweeps measured KEEP = {keep}, TAKE = {take}")
