# Writes the digital LDO decks into the current directory: "loop" writes loop.cir and schedule.txt, the transistor loop (128 dldo_unit switch units driven by the controller RTL through ngspice d_cosim from dldo_ctrl.so, four of the ADC's StrongARM comparators at power_manager's sizes clocked on the inverted 50 MHz clock comparing 0.6 of the rail from ten identical rppd units with ladder taps picked by tap_mux.cir from the one-hot DVFS select, a 201-unit ladder on the analog rail at ref.inc's measured vref_v, 2 nF of MOS decoupling and the cpu's measured per-cycle current from cycles.txt scaled by rail / 1.2 V), with "model" the real-number model instead (each unit the measured current iunit of the rail from unit.inc switched after the measured delays t_on and t_off, each comparator an ideal compare sampled on the inverted clock's rising edge), with "mem" the fixed 1.2 V vdd_mem copy under the macros' current, with "short" only the start-up segment and with "trap" the trapezoidal method instead of gear; "check" writes cosim_check.cir, the controller alone under each comparator input in turn, both coarse ones together last, every output to check.txt for dldo_results.py and dldo_loop.py; "ref" writes ref.cir, bandgap_ldo's bandgap and LDO with the ladder on the LDO output, its operating point to ref.txt; "unit" writes unit.cir, one switch unit's current against the rail (iv.txt) and its turn-on and turn-off delays (delay.txt).
import sys
from pathlib import Path

N, LADDER_UNITS, TAPS, PERIOD, EDGE = 128, 201, (90, 100, 110, 120), 20e-9, 10e-9
WINDOWS = {"fl": -1, "fh": 1, "cl": -5, "ch": 5}
CPU = [("s0", 0.0, 1.0, 90, "idle", "start"), ("s1", 1.0, 1.8, 90, "active", "load_up"), ("s2", 1.8, 2.6, 100, "active", "dvfs_up"),
       ("s3", 2.6, 3.4, 110, "active", "dvfs_up"), ("s4", 3.4, 4.2, 120, "active", "dvfs_up"), ("s5", 4.2, 5.4, 90, "active", "dvfs_down"),
       ("s6", 5.4, 6.2, 120, "active", "dvfs_up"), ("s7", 6.2, 7.0, 120, "idle", "load_down"), ("s8", 7.0, 7.8, 120, "active", "load_up")]
MEM = [("s0", 0.0, 1.0, 120, "idle", "start"), ("s1", 1.0, 1.8, 120, "active", "load_up"), ("s2", 1.8, 2.6, 120, "idle", "load_down")]

def params(path):
    return " ".join(w for l in Path(path).read_text().splitlines() if l.startswith(".param") for w in l.split()[1:])

def scoped(netlist, sizes, name):
    return "\n".join(l + f" params: {params(sizes)}" if l.startswith(f".subckt {name} ") else l for l in Path(netlist).read_text().splitlines()) + "\n"

def pwl(points):
    return "pwl(" + " ".join(f"{t:.6g} {v:.6g}" for t, v in points) + ")"

def load_points(segments, column):
    rows = [l.split() for l in Path("cycles.txt").read_text().splitlines() if l.strip()]
    level = {int(r[0]): float(r[column]) for r in rows}
    idle, active = (level[1] + level[2]) / 2, [level[k] for k in sorted(level) if k >= 4]
    points, now, index, was = [(0.0, idle)], idle, 0, "idle"
    for name, a, b, tap, load, kind in segments:
        if load == "idle":
            if now != idle:
                edge = EDGE + PERIOD * -(-(a * 1e-6 - EDGE) // PERIOD)
                points += [(edge, now), (edge + 1e-10, idle)]
                now = idle
        else:
            index = 0 if was == "idle" else index
            edge = EDGE + PERIOD * -(-(a * 1e-6 - EDGE) // PERIOD)
            while edge < b * 1e-6 - 1e-12:
                new = active[index % len(active)]
                points += [(edge, now), (edge + 1e-10, new)]
                now, index, edge = new, index + 1, edge + PERIOD
        was = load
    return points

def selects(segments, vdd):
    out = []
    for j, tap in enumerate(TAPS):
        points, last = [], None
        for name, a, b, t, load, kind in segments:
            level = vdd if t == tap else 0.0
            if last is None:
                points.append((0.0, level))
            elif level != last:
                points += [(a * 1e-6, last), (a * 1e-6 + 1e-10, level)]
            last = level
        out.append(f"VS{j} s{j} 0 {pwl(points)}\nVS{j}B s{j}b 0 {pwl([(t, vdd - v) for t, v in points])}")
    return "\n".join(out)

def loop(model, mem, short, trap):
    segments = MEM if mem else CPU[:1] if short else CPU
    t_end = segments[-1][2] * 1e-6
    Path("schedule.txt").write_text(f"t_end {t_end:.6g}\n" + "".join(f"{n} {a * 1e-6:.6g} {b * 1e-6:.6g} {tap} {load} {kind}\n" for n, a, b, tap, load, kind in segments))
    Path("shifter_scoped.cir").write_text(scoped("shifter_hv.cir", "shifter_hv_sizes.inc", "shifter_hv"))
    ladder = "\n".join(f"XL{k} {f'l{k + 1}' if k < 200 else 'top'} {f'l{k}' if k else 0} 0 rppd w={{w_lad}} l={{l_lad}} mm_ok={{mm}}" for k in range(201))
    divider = "\n".join(f"XD{k} {'out' if k == 9 else 'fb' if k == 5 else f'dv{k + 1}'} {'fb' if k == 6 else f'dv{k}' if k else 0} 0 rppd w={{w_r}} l={{l_r}} mm_ok={{mm}}" for k in range(10))
    sel = " ".join(f"s{j}" for j in range(4)) + " " + " ".join(f"s{j}b" for j in range(4))
    muxes = "\n".join(f"XM{c.upper()} t{c} {' '.join(f'l{tap + d}' for tap in TAPS)} {sel} vdd 0 tap_mux" for c, d in WINDOWS.items())
    ons = " ".join(f"d{i}" for i in reversed(range(N)))
    analog = " ".join(f"on{i}" for i in reversed(range(N)))
    count = " ".join(f"ct{i}" for i in reversed(range(8)))
    drive = " ".join(f"dr{i}" for i in reversed(range(8)))
    if model:
        array = ("\n".join(f"AB{i} d{i} e{i} unit_delay" for i in range(N)) + "\n.model unit_delay d_buffer(rise_delay={t_on} fall_delay={t_off})\n"
                 f"AOUT [{' '.join(f'e{i}' for i in reversed(range(N)))}] [{analog}] tovolts\n"
                 f"BSW vin out i = iunit(v(out)) * ({' + '.join(f'v(on{i})' for i in range(N))}) / {{vdd_v}}")
        comparators = ("BFL lo 0 v = v(tfl) > v(fb) ? {vdd_v} : 0\nBFH hi 0 v = v(fb) > v(tfh) ? {vdd_v} : 0\n"
                       "BCL flo 0 v = v(tcl) > v(fb) ? {vdd_v} : 0\nBCH fhi 0 v = v(fb) > v(tch) ? {vdd_v} : 0\n"
                       "AIN [clk rst clkb lo hi flo fhi] [dclk drst dclkb rlo rhi rflo rfhi] tobits\n"
                       + "\n".join(f"AF{k} r{k} dclkb NULL NULL d{k} NULL sample" for k in ("lo", "hi", "flo", "fhi"))
                       + "\n.model sample d_dff(clk_delay=100p set_delay=100p reset_delay=100p)")
        includes = ".include unit.inc"
    else:
        array = "\n".join(f"XU{i} on{i} out vin vdd 0 dldo_unit" for i in range(N)) + f"\nAOUT [{ons}] [{analog}] tovolts"
        comparators = ("XCFL tfl fb clkb lo lon vdd 0 comparator\nXCFH fb tfh clkb hi hin vdd 0 comparator\n"
                       "XCCL tcl fb clkb flo flon vdd 0 comparator\nXCCH fb tch clkb fhi fhin vdd 0 comparator\n"
                       "AIN [clk rst lo hi flo fhi] [dclk drst dlo dhi dflo dfhi] tobits")
        includes = ".include comparator_sizes.inc\n.include comparator.cir"
    lw = pwl(load_points(segments, 2 if mem else 1))
    text = f"""* Digital LDO loop: written by tests/make_loop.py.
.include corner.inc
.include ref.inc
{includes}
.include shifter_scoped.cir
.include dldo_sizes.inc
.include dldo_unit.cir
.include tap_mux.cir
{'' if trap else '.option method=gear'}
VIN vin 0 {{vin_v}}
VDD vdd 0 {{vdd_v}}
VREF top 0 {{vref_v}}
VCLK clk 0 pulse(0 {{vdd_v}} 10n 50p 50p 9.95n 20n)
VCLKB clkb 0 pulse({{vdd_v}} 0 10n 50p 50p 9.95n 20n)
VRST rst 0 pwl(0 0 100n 0 101n {{vdd_v}})
{selects(segments, 1.2)}
VLW lw 0 {lw}
{array}
XDC 0 out 0 0 sg13_lv_nmos w={{w_dc}} l={{l_dc}} m={{m_dc}}
BLOAD out 0 i = v(lw) * max(v(out), 0) / 1.2
{divider}
{ladder}
{muxes}
{comparators}
.model tobits adc_bridge(in_low={{vdd_v / 3}} in_high={{2 * vdd_v / 3}})
ACTL [dclk drst dlo dhi dflo dfhi] [{ons} {count} {drive}] null ctrl
.model ctrl d_cosim simulation="./dldo_ctrl.so"
.model tovolts dac_bridge(out_low=0 out_high={{vdd_v}} t_rise=100p t_fall=100p)
.tran 1n {t_end:.6g}
.control
run
wrdata loop.txt v(out)
quit
.endc
.end
"""
    Path("loop.cir").write_text(text)

def check():
    ons = " ".join(f"d{i}" for i in reversed(range(N)))
    count = " ".join(f"ct{i}" for i in reversed(range(8)))
    drive = " ".join(f"dr{i}" for i in reversed(range(8)))
    analog = " ".join(f"on{i}" for i in reversed(range(N)))
    text = f"""* Digital LDO controller port check: written by tests/make_loop.py.
VCLK clk 0 pulse(0 1.2 10n 50p 50p 9.95n 20n)
VRST rst 0 pwl(0 0 100n 0 101n 1.2)
VLO lo 0 pwl(0 1.2 400n 1.2 401n 0 760n 0 761n 1.2 799n 1.2 800n 0)
VHI hi 0 pwl(0 0 400n 0 401n 1.2 700n 1.2 701n 0)
VFL flo 0 pwl(0 1.2 300n 1.2 301n 0 799n 0 800n 1.2 880n 1.2 881n 0)
VFH fhi 0 pwl(0 0 400n 0 401n 1.2 600n 1.2 601n 0 799n 0 800n 1.2 880n 1.2 881n 0)
AIN [clk rst lo hi flo fhi] [dclk drst dlo dhi dflo dfhi] tobits
.model tobits adc_bridge(in_low=0.4 in_high=0.8)
ACTL [dclk drst dlo dhi dflo dfhi] [{ons} {count} {drive}] null ctrl
.model ctrl d_cosim simulation="./dldo_ctrl.so"
AOUT [{ons} {count} {drive}] [{analog} {" ".join(f"cta{i}" for i in reversed(range(8)))} {" ".join(f"drv{i}" for i in reversed(range(8)))}] tovolts
.model tovolts dac_bridge(out_low=0 out_high=1.2 t_rise=100p t_fall=100p)
.tran 1n 900n
.control
run
wrdata check.txt v(lo) v(hi) v(flo) v(fhi) v(rst) {" ".join(f"v(cta{i})" for i in range(8))} {" ".join(f"v(drv{i})" for i in range(8))} {" ".join(f"v(on{i})" for i in range(N))}
quit
.endc
.end
"""
    Path("cosim_check.cir").write_text(text)

def ref():
    ladder = "\n".join(f"XL{k} {f'l{k + 1}' if k < 200 else 'top'} {f'l{k}' if k else 'vss'} vss rppd w={{w_lad}} l={{l_lad}} mm_ok={{mm}}" for k in range(201))
    text = f"""* Analog rail with the DLDO ladder on it: written by tests/make_loop.py.
.include corner.inc
.include bandgap_sizes.inc
.include bandgap.cir
.include ldo_sizes.inc
.include ldo.cir
.subckt dldo_ladder top vss params: {" ".join(w for w in params("dldo_sizes.inc").split() if w.startswith(("w_lad=", "l_lad=")))}
{ladder}
.ends dldo_ladder
VDD vdd 0 {{vin_v}}
X1 vref vg vdd 0 vdd 0 0 0 bandgap
X2 vout vout vref vg vdd 0 ldo
XLAD vout 0 dldo_ladder
.control
op
let vref_v = v(vout)
echo "vref_v $&vref_v bandgap_v $&v(vref)" > ref.txt
quit
.endc
.end
"""
    Path("ref.cir").write_text(text)

def unit():
    Path("shifter_scoped.cir").write_text(scoped("shifter_hv.cir", "shifter_hv_sizes.inc", "shifter_hv"))
    text = """* One DLDO switch unit's current and delays: written by tests/make_loop.py.
.include corner.inc
.include shifter_scoped.cir
.include dldo_sizes.inc
.include dldo_unit.cir
VIN vin 0 {vin_v}
VDD vdd 0 {vdd_v}
VON on 0 dc {vdd_v} pulse(0 {vdd_v} 5n 100p 100p 20n 60n)
VOUT out 0 1.0
XU on out vin vdd 0 dldo_unit
.control
dc VOUT 0.7 1.4 0.02
let iu = i(VOUT)
wrdata iv.txt iu
tran 10p 50n
let iu = i(VOUT)
meas tran full avg iu from=20n to=25n
let half = full / 2
meas tran up when iu=$&half rise=1
meas tran down when iu=$&half fall=1
let t_on_s = up - 5.05n
let t_off_s = down - 25.15n
let t_end_s = time[length(time) - 1]
echo "unit t_on_s $&t_on_s t_off_s $&t_off_s t_end_s $&t_end_s full_a $&full" > delay.txt
quit
.endc
.end
"""
    Path("unit.cir").write_text(text)

def sense():
    vref = float(Path("ref.inc").read_text().split("vref_v=")[1].split()[0])
    ladder = "\n".join(f"XL{k} {f'l{k + 1}' if k < 200 else 'top'} {f'l{k}' if k else 0} 0 rppd w={{w_lad}} l={{l_lad}} mm_ok={{mm}}" for k in range(201))
    divider = "\n".join(f"XD{k} {'out' if k == 9 else 'fb' if k == 5 else f'dv{k + 1}'} {'fb' if k == 6 else f'dv{k}' if k else 0} 0 rppd w={{w_r}} l={{l_r}} mm_ok={{mm}}" for k in range(10))
    sel = " ".join(f"s{j}" for j in range(4)) + " " + " ".join(f"s{j}b" for j in range(4))
    muxes = "\n".join(f"XM{c.upper()} t{c} {' '.join(f'l{tap + d}' for tap in TAPS)} {sel} vdd 0 tap_mux" for c, d in WINDOWS.items())
    runs = []
    for j, tap in enumerate(TAPS):
        out = vref * tap / LADDER_UNITS / 0.6
        runs.append("\n".join([f"alter VS{i} dc = {1.2 if i == j else 0}\nalter VS{i}B dc = {0 if i == j else 1.2}" for i in range(4)])
                    + f"\nalter VOUT dc = {out:.6g}\ndestroy all\n" + "".join(f"let {c}_{e} = nan\n" for c in (*WINDOWS, "fb") for e in ("a", "b"))
                    + "tran 10p 200n\n"
                    + "".join(f"meas tran {c}_{e} find v({'fb' if c == 'fb' else 't' + c}) at={t}\n" for c in (*WINDOWS, "fb") for e, t in (("a", "180.05n"), ("b", "180.35n")))
                    + "echo \"sense " + str(tap) + " " + " ".join(f"{c}_{e} $&{c}_{e} ideal_{c} {vref * (tap + d) / LADDER_UNITS:.6g}" for c, d in WINDOWS.items() for e in ("a", "b"))
                    + " " + " ".join(f"fb_{e} $&fb_{e}" for e in ("a", "b")) + f" ideal_fb {0.6 * out:.6g}\" >> sense.txt")
    text = f"""* DLDO sensing at the comparators' sampling edge: written by tests/make_loop.py.
.include corner.inc
.include comparator_sizes.inc
.include comparator.cir
.include dldo_sizes.inc
.include tap_mux.cir
VDD vdd 0 {{vdd_v}}
VREF top 0 {vref:.6g}
VOUT out 0 1.0
VCLKB clkb 0 pulse({{vdd_v}} 0 10n 50p 50p 9.95n 20n)
{chr(10).join(f"VS{j} s{j} 0 0{chr(10)}VS{j}B s{j}b 0 1.2" for j in range(4))}
{divider}
{ladder}
{muxes}
XCFL tfl fb clkb lo lon vdd 0 comparator
XCFH fb tfh clkb hi hin vdd 0 comparator
XCCL tcl fb clkb flo flon vdd 0 comparator
XCCH fb tch clkb fhi fhin vdd 0 comparator
.control
let nan = 1e400 - 1e400
echo "sensing residues" > sense.txt
{chr(10).join(runs)}
quit
.endc
.end
"""
    Path("sense.cir").write_text(text)

if __name__ == "__main__":
    args = sys.argv[1:]
    if args[0] == "check":
        check()
    elif args[0] == "ref":
        ref()
    elif args[0] == "unit":
        unit()
    elif args[0] == "sense":
        sense()
    else:
        loop("model" in args, "mem" in args, "short" in args, "trap" in args)
