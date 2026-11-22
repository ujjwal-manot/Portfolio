# Writes loop.cir, the transistor-level digital LDO testbench, into the current directory: 128 switch units (dldo_unit.cir) driven by the controller RTL through ngspice d_cosim (dldo_ctrl.so from vlnggen), four window comparators (the ADC's StrongARM with power_manager's sizes) clocked on the inverted 50 MHz clock comparing a divider of ten identical rppd units on the rail (0.6 V at the 1.0 V setpoint) against a ladder of 201 identical units on the 1.206 V bandgap output (6 mV per unit, taps at 0.570, 0.594, 0.606 and 0.630 V), 2 nF of MOS decoupling and a load drawing the current of load.inc's source lw (volts read as amps) scaled by rail/1.0 V as switched capacitance does; vout and the units on are written every 10 ns to loop.txt.
import sys

N = 128
units = "\n".join(f"XU{i} on{i} out vin vdd 0 dldo_unit" for i in range(N))
taps = {95: "r95", 99: "r99", 101: "r101", 105: "r105", 201: "vref"}
ladder = "\n".join(f"XL{k} {taps.get(k + 1, f'l{k + 1}')} {taps.get(k, f'l{k}') if k else 0} 0 rppd w={{w_r}} l={{l_r}} mm_ok={{mm}}" for k in range(201))
divider = "\n".join(f"XD{k} {'out' if k == 9 else 'fb' if k == 5 else f'dv{k + 1}'} {'fb' if k == 6 else f'dv{k}' if k else 0} 0 rppd w={{w_r}} l={{l_r}} mm_ok={{mm}}" for k in range(10))
ons = " ".join(f"d{i}" for i in reversed(range(N)))
analog = " ".join(f"on{i}" for i in reversed(range(N)))
drive = " ".join(f"dr{i}" for i in reversed(range(8)))
count = " ".join(f"ct{i}" for i in reversed(range(8)))
drive_a = " ".join(f"drv{i}" for i in reversed(range(8)))
text = f"""* Digital LDO loop: written by tests/make_loop.py.
.include corner.inc
.include load.inc
.include comparator_sizes.inc
.include comparator.cir
.include shifter_hv_sizes.inc
.include shifter_hv.cir
.include dldo_sizes.inc
.include dldo_unit.cir
.option method=gear
VIN vin 0 {{vin_v}}
VDD vdd 0 {{vdd_v}}
VREF vref 0 1.206
VCLK clk 0 pulse(0 {{vdd_v}} 10n 50p 50p 9.95n 20n)
VCLKB clkb 0 pulse({{vdd_v}} 0 10n 50p 50p 9.95n 20n)
VRST rst 0 pwl(0 0 100n 0 101n {{vdd_v}})
{units}
XDC 0 out 0 0 sg13_lv_nmos w={{w_dc}} l={{l_dc}} m={{m_dc}}
BLOAD out 0 i = v(lw) * max(v(out), 0) / 1.0
{divider}
{ladder}
XCFL r99 fb clkb lo lon vdd 0 comparator
XCFH fb r101 clkb hi hin vdd 0 comparator
XCCL r95 fb clkb flo flon vdd 0 comparator
XCCH fb r105 clkb fhi fhin vdd 0 comparator
AIN [clk rst lo hi flo fhi] [dclk drst dlo dhi dflo dfhi] tobits
.model tobits adc_bridge(in_low={{vdd_v / 3}} in_high={{2 * vdd_v / 3}})
ACTL [dclk drst dlo dhi dflo dfhi] [{ons} {count} {drive}] null ctrl
.model ctrl d_cosim simulation="./dldo_ctrl.so"
AOUT [{ons} {drive}] [{analog} {drive_a}] tovolts
.model tovolts dac_bridge(out_low=0 out_high={{vdd_v}} t_rise=100p t_fall=100p)
.tran 1n {{t_end}}
.control
run
wrdata loop.txt v(out) {" ".join(f"v(drv{i})" for i in range(8))}
.endc
.end
"""
open(sys.argv[1] if len(sys.argv) > 1 else "loop.cir", "w").write(text)
