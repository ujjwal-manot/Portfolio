# EdgeSense-130 chip

IHP SG13G2 130 nm, VDD = 1.2 V, all low-voltage devices (`sg13_lv_nmos`, `sg13_lv_pmos`).

```
          0.2 .. 1.0 V                       8-bit codes            AXI4-Stream             AXI4-Stream
sensor ---> [opamp] ---> [adc] -------------------> [fifo_bridge] ----------------> [cpu]
            gain -1      1 MS/s                      10 MHz -> 50 MHz                filter + detector
            about 0.6 V  clk_adc = 10 MHz            16 deep                         clk_sys = 50 MHz
```

## Clocks and resets

| Name | Frequency | Used by |
|---|---|---|
| clk_adc | 10 MHz | adc logic, write side of fifo_bridge |
| clk_sys | 50 MHz | read side of fifo_bridge, cpu |

The two clocks are unrelated. Resets are active low (`rst_n`), asserted asynchronously, released synchronously in each clock domain.

Both clocks come in on pins from oscillators on the board; nothing on the chip makes them. `frac_n_pll` clocks only `serdes_link`. So their jitter is a property of the board, never measured here, and every timing check runs with zero jitter. What the chip needs from the board, worked out rather than measured:

- clk_sys: the worst setup slack is about 15 ns of a 20 ns period, so cycle-to-cycle jitter far below that changes nothing.
- clk_adc: sampling a full-scale 50 kHz sine with rms jitter s limits SNR to -20 log10(2 pi 50 kHz s). Jitter alone equal to the 49.9 dB of an ideal 8-bit converter (s = 10 ns) would cost 3 dB of total SNR; for under 0.5 dB, the jitter noise must stay under 12% of the quantization noise, so its SNR must reach 59.1 dB and s must stay below 3.5 ns rms. That is the number the board oscillator has to meet.

## Signal levels

| Signal | Value |
|---|---|
| Sensor input | 0.2 to 1.0 V, up to 50 kHz |
| VCM (mid-rail reference) | 0.6 V |
| ADC reference | vref_lo = 0.2 V, vref_hi = 1.0 V |
| 1 LSB | 3.125 mV |
| Largest sensor signal | 0.357 V peak around 0.6 V (-1 dBFS); the 43.5 mV (13.9 LSB) left at each end of the ADC range is the budget for every offset and gain error between sensor and code |

## Block interfaces

### opamp

```
.subckt opamp inp inn out vdd vss ibias
```

`ibias` takes a 10 uA reference current into the chip (a current sink to vss inside the opamp).

Test setup: inverting amplifier, Rin = Rf = 20 k, `inp` at 0.6 V, 2.05 pF load. Output = 1.2 V - input.

| Spec | Target |
|---|---|
| DC gain | >= 66 dB |
| GBW | >= 20 MHz |
| Phase margin (beta = 0.5 loop, all corners, Monte Carlo) | >= 60 deg |
| Monte Carlo yield, every spec in this table combined | one-sided 95% lower bound of 99% or more (at least 299 seeds with no failure); a point estimate alone does not count |
| Slew rate | >= 10 V/us |
| Settling, 0.8 V step to 1.56 mV | <= 200 ns |
| Error at the -1 dBFS peak: 2 x input offset (noise gain 2) + gain error x 0.357 V | <= 37.6 mV (the 43.5 mV headroom less the ADC's allowed 1 LSB offset and 2 LSB full-scale gain error, scaled to the peak) |
| Settling into the ADC's real capacitor DAC, through its switches | <= 1.56 mV at the end of the 200 ns sample |
| Supply current | <= 500 uA |

Requirement the opamp puts on `bandgap_ldo` (measured in `projects/opamp/results/corners.log`): at 1.08 V the output stops short of 1.0 V at the hot corners, at 1.16 V it reaches it at every corner. So the analog rail must stay at or above 1.16 V: with a 1.2 V target, regulation error plus load-step droop must stay under 40 mV, the bandgap_ldo section below takes this as its floor.

### adc

Analog parts:

```
.subckt comparator inp inn clk outp outn vdd vss
.subckt cap_dac top vin vcm vref_hi vref_lo samp d7 d6 d5 d4 d3 d2 d1 d0 vdd vss
```

The comparator is a StrongARM latch. It resets while `clk` is low and decides while `clk` is high: `outp` high means `inp > inn`.

The DAC uses 256 unit capacitors of about 8 fF (2.05 pF in total) with bottom-plate sampling:
- While `samp` is high, every bottom plate follows `vin` and the top plate is held at `vcm`.
- After that, bottom plate `k` connects to `vref_hi` when `dk` is 1 and to `vref_lo` when it is 0.

Digital part, `sar_logic.sv`:

```
module sar_logic (
  input  logic       clk, rst_n, comp_out,
  output logic       samp, comp_clk,
  output logic [7:0] dac,
  output logic       m_tvalid,
  input  logic       m_tready,
  output logic [7:0] m_tdata,
  output logic       m_tlast,
  output logic       overflow
);
```

Each sample takes 10 clk_adc cycles:
- 2 cycles with `samp` high.
- 8 bit trials, MSB first. Each trial sets `dac` on the rising edge, the comparator fires in the low half of the cycle, and the bit is kept on the next rising edge.

Every 64th sample sets `m_tlast`. The ADC cannot wait, so if `m_tready` is low when a sample is ready, the sample is dropped and the sticky `overflow` flag is set.

| Spec | Target |
|---|---|
| ENOB (coherent FFT, -0.5 dBFS sine) | >= 7.5 bits |
| DNL / INL | within +-0.5 LSB / +-1 LSB |
| Offset / gain error | within +-1 LSB / +-2 LSB |

### fifo_bridge

```
module fifo_bridge (
  input  logic       s_clk, s_rst_n,
  input  logic       s_tvalid,
  output logic       s_tready,
  input  logic [7:0] s_tdata,
  input  logic       s_tlast,
  input  logic       m_clk, m_rst_n,
  output logic       m_tvalid,
  input  logic       m_tready,
  output logic [7:0] m_tdata,
  output logic       m_tlast
);
```

Inside: `async_fifo` (9 bits wide, 16 deep, Gray-code pointers, two-flop synchronizers), then `skid_buffer` on the read side so `s_tready` and `m_tready` never form a combinational path. No word is ever lost, duplicated or reordered.

### cpu

```
module cpu (
  input  logic        clk, rst_n,
  output logic [31:0] imem_addr,
  input  logic [31:0] imem_data,
  output logic [31:0] dmem_addr, dmem_wdata,
  output logic [3:0]  dmem_wstrb,
  output logic        dmem_read,
  input  logic [31:0] dmem_rdata,
  input  logic        s_tvalid,
  output logic        s_tready,
  input  logic [7:0]  s_tdata,
  input  logic        s_tlast,
  output logic        retire_valid,
  output logic [31:0] retire_pc, retire_instr, retire_rd_data,
  output logic [4:0]  retire_rd,
  output logic        retire_intr, sleep,
  output logic [3:0]  retire_cause
);
```

- RV32I, 5 stages (IF, ID, EX, MEM, WB), with forwarding, a load-use stall and a 2-bit branch predictor with a 16-entry BTB.
- Instruction and data memory are outside the core and synchronous, like the IHP SRAM macros (`RM_IHPSG13_1P_2048x32_c2_bm_bist`, 8 KB each): in each cycle the core drives the next fetch address, and the address, write data and byte strobes of the store or load in EX; the memory takes them at the closing edge and its read data arrives in the next cycle (the fetch's IF, the load's MEM).
- `retire_*` reports every finished instruction, so a testbench can check each one against `helpers/cpu_model.py`. `retire_intr` marks the slot of an interrupt taken in place of the instruction at `retire_pc`, with its cause in `retire_cause`.
- Machine mode only: Zicsr and the machine CSRs (mstatus, misa, mie, mip, mtvec with vectored interrupts, mscratch, mepc, mcause, mtval, mcycle, minstret, mcountinhibit, the ID registers reading 0), traps for illegal instructions, ecall, ebreak and misaligned loads, stores and jump targets, mret.
- Interrupts: timer (cause 7, mtime >= mtimecmp) and external (cause 11, high while a stream sample waits). Traps and interrupts are taken in EX, where instructions commit.
- `wfi` holds the pipeline and raises `sleep` until an enabled interrupt is pending; `sleep` is there for a clock gate around the core (mtime keeps counting).

Memory map:

| Address | Read | Write |
|---|---|---|
| 0x0000_0000 .. 0x0000_FFFF | instruction and data RAM (64 KB) | RAM |
| 0x1000_0000 | stream: bit 31 = valid, bit 8 = last, bits 7..0 = data; reading pops the word when valid | |
| 0x1000_0010 | mcycle, low word | |
| 0x1000_0014 | minstret, low word | |
| 0x1000_0018 | branch counter | |
| 0x1000_001C | mispredict counter | |
| 0x1000_0020 / 0x1000_0024 | mtime low / high (counts every clock from reset) | |
| 0x1000_0028 / 0x1000_002C | mtimecmp low / high (all ones after reset) | mtimecmp low / high |
| 0x1000_0100 | | test result: 1 = pass, any other value = fail code |

Firmware flips each code back with `code ^ 0xFF`, because the opamp inverts.

Cycle timing (the contract `cpu_model.Timed` checks the RTL against; edges are rising clock edges counted from the first one after reset is released):
- An instruction spends one cycle in EX, then one in MEM and one in WB; MEM and WB never stall.
- mtime is k during the cycle after edge k. mcycle counts the same edges, except that a cycle with mcountinhibit.CY set adds nothing, and a CSR write sets the value seen from the next cycle on.
- A store to mtimecmp takes effect two edges after its EX cycle (at the edge that ends its MEM cycle).
- The timer interrupt is pending in any cycle where mtime >= mtimecmp, compared on all 64 bits.
- The external interrupt is pending in a cycle if `s_tvalid` was high at the edge that started it (one register).
- An interrupt is taken in place of the instruction in EX in any cycle where mstatus.MIE is set and an enabled interrupt is pending; external goes before timer. No instruction may commit in such a cycle.
- A load from the stream address returns `s_tvalid`, `s_tlast` and `s_tdata` as they are at the edge that ends its MEM cycle; the counters at 0x1000_0010..1C give the count after every instruction up to and including the load itself.
- The branch counter counts committed conditional branches. The mispredict counter counts committed instructions (all but mret) whose following fetched instruction was not the one that executes next.

| Spec | Target |
|---|---|
| riscv-tests rv32ui | all pass, every retired instruction matches the model |
| Clock | 50 MHz at the slow corner (1.08 V, 125 C) |
| Filter (8-tap FIR + threshold per sample) | <= 3200 cycles per 64-sample frame |

### bandgap_ldo

```
.subckt bandgap vref vg vdd vss trim3 trim2 trim1 trim0
.subckt ldo vout fb vref vg vdd vss
```

Both run from the 3.3 V supply on thick-oxide devices. `vg` carries the bandgap's PTAT branch current to the LDO's bias mirrors; `fb` is tied to `vout` (unity gain).

| Spec | Target |
|---|---|
| Bandgap tempco, -40 to 125 C, box method | <= 30 ppm/C at every corner, and a Monte Carlo yield whose one-sided 95% lower bound is 99% or more (at least 299 seeds with no failure) |
| LDO output | vref, about 1.206 V |
| LDO rated load | 0 to 2 mA (the analog rail draws under 0.25 mA: the opamp's worst supply current is 0.225 mA in `projects/opamp/results/corners.log`) |
| Rail through a 0 to 0.5 mA step in 100 ns (twice the opamp's worst current) | >= 1.16 V, the opamp's floor above |
| Rail after a 2 mA step, and at start-up | <= 1.32 V, the thin-oxide limit |
| Load regulation, 0 to 2 mA / line regulation, 3.0 to 3.6 V | <= 5 mV / <= 10 mV/V |
| PSRR at 1 kHz / 1 MHz | >= 40 dB / >= 20 dB |
| Phase margin, every load from 0 to 2 mA | >= 45 deg |
| Bandgap and LDO current together | <= 200 uA at 27 C and below; above that it may grow with absolute temperature (265 uA at 125 C), since every bias is a copy of the bandgap's PTAT current |

The first LDO pick in `plan.md` (0 to 20 mA in 100 ns with under 40 mV of droop, under 100 uA) is out of reach without an external capacitor: 40 mV on the 100 pF output is 4 pC, which a 20 mA ramp uses up in 6.3 ns, while the pass gate must swing about 0.5 V; and with a follower pass device the light-load output pole is its gm over the output capacitance, so the bleed current, not the compensation, sets how fast the loop can be at no load. Under 100 uA total the loop was either unstable at no load or let a 0.25 mA step pull the rail under 1.16 V. The targets above come from the loads the rail really has. The current limit was first a flat 200 uA, met only at 27 C: with PTAT bias the total reached 246 uA at ff 125 C. A flat bleed (an rppd resistor from the output) cut that to 201 uA but dropped the no-load phase margin to 43 deg, because at fixed current a follower's gm falls as temperature rises (`make bleed_study` keeps both runs). The design keeps the PTAT bleed, which holds gm and the light-load pole over temperature, so the limit now states what that costs.

### power_manager

Two supplies come out of it, both from the 3.3 V input:

| Rail | Voltage | Feeds | Load |
|---|---|---|---|
| vdd_cpu | 0.90, 1.00, 1.10 or 1.20 V, picked by a cpu register | the cpu's cells | 9.0 mW at 1.2 V, 50 MHz, typical corner (7.5 mA), from `projects/cpu/results/power.log` |
| vdd_mem | 1.20 V fixed | both SRAM macros, fifo_bridge, the clock divider and the power manager's own logic | the macros' 3.5 mW (2.9 mA) in the same report, plus the rest |

Why two: the IHP SRAM macros are characterized only at 1.08, 1.2 and 1.32 V, so below 1.08 V there are no access times, setup times or read and write margins for them. Product teams keep such macros on a fixed rail and level-shift what drives them; every macro input the cpu drives (address, data, byte mask, enables and the clock) goes up through a level shifter from vdd_cpu to vdd_mem. Macro outputs and fifo_bridge outputs come down into vdd_cpu without one (a 1.2 V input on a 0.9 V gate turns its PMOS fully off and stays inside the oxide limit); `s_tready` goes up through one. Running the macros lower is a separate study and only moves the rail if it proves a margin.

Each rail is a digital LDO: 128 thick-oxide PMOS switch units from the 3.3 V input, 2 nF of MOS decoupling, four clocked comparators (a fine and a coarse window) comparing 0.6 of the rail with taps of a 201-unit resistor ladder on the 1.2 V analog rail from bandgap_ldo, and the controller RTL (`design/dldo_ctrl.sv`) at 50 MHz. vdd_cpu's setpoint is ladder tap 90, 100, 110 or 120 (0.90 to 1.20 V), chosen by a 2-bit cpu register through transmission-gate muxes; vdd_mem uses tap 120 alone. The windows are one ladder unit (fine) and five units (coarse) either side of the setpoint tap, so about 10 and 50 mV on the rail at 1.0 V.

| Spec | Target |
|---|---|
| Regulation: mean rail over the last 400 ns of each setpoint, cpu at its measured active load | within 2% of the setpoint (18, 20, 22, 24 mV), the setpoint taken from the ladder ratio and the analog rail as measured with the ladder on it |
| Ripple (limit cycle), peak to peak over the same window | at most 3% of the setpoint (27, 30, 33, 36 mV) |
| Rail envelope under the cpu's measured load, including its idle-to-active transition, with no clock stretch | inside the setpoint +-5% (so the cpu's STA at each state is run at the setpoint minus 5%; below that the droop detector stretches the clock) |
| DVFS up (0.9 to 1.0, 1.0 to 1.1, 1.1 to 1.2 and 0.9 to 1.2 V), from the register change to the rail staying inside the new setpoint +-3.5% (the 2% regulation plus half the 3% ripple) | at most 500 ns, never above the new setpoint +5% nor 1.32 V |
| DVFS down (1.2 to 0.9 V) at the cpu's active load | at most 1 us, never below the new setpoint -5%; the fall is the load discharging the decoupling, so firmware lowers the clock first and a lighter load falls slower |
| vdd_mem, the same loop at tap 120 under the macros' measured load | regulation, ripple and envelope as above at 1.20 V, so 1.14 to 1.26 V, inside the macros' 1.08 to 1.32 V |
| Window comparators, 100-run Monte Carlo at tt 27 C | 3 sigma of input offset under half the fine window (3 mV at the comparator input) |
| vin brown-out (design 2.894 V falling, 2.944 V rising, 50 mV hysteresis) | falling trip in [2.80, 3.00) V, rising trip under 3.00 V and above the falling trip, hysteresis at least 20 mV: the rated input is 3.0 to 3.6 V, and the 2.80 V floor makes the copy with the threshold 100 mV off fail |
| vdd_mem brown-out (design 1.106 V falling, 1.126 V rising, 20 mV hysteresis) | falling trip in [1.08, 1.14] V, rising trip at most 1.17 V, hysteresis at least 10 mV: the SRAM macros are characterized down to 1.08 V, 1.14 V is the coarse window's low edge scaled to 1.2 V, and 1.17 V sits under the fine window's low edge (1.188 V) |
| Power-on reset | rst_n held low from 0 V until both brown-out comparators read good, at every corner, for 10 us and 1 ms input ramps |

There is no brown-out detector on vdd_cpu, since DVFS moves it on purpose and a droop there goes to the droop detector and the clock stretch, and none on the analog rail.

The load is measured, not assumed: OpenSTA reports the cpu cells' power from `projects/cpu/build/cpu_gates.vcd` (the filter firmware on the mapped netlist, typical library, 1.2 V, 25 C) in one-cycle windows set between clock edges, and the current is that power over 1.2 V, scaled by rail / 1.2 V at the lower setpoints (switched charge, at the same 50 MHz clock, which overstates the load wherever a state runs slower). The gate run never sleeps (`sleep` stays low), so the idle level is taken from its reset cycles, where the clock runs and the logic is held, the same as `wfi` with no clock gating; the idle-to-active transition is the measured cycles after reset release, not a step. vdd_mem's load is the macros' share of the same windows; fifo_bridge, the clock divider and the power manager's own logic are not in it yet.

Loop corners: tt 27 C with 3.3 V in, ss 125 C with 3.0 V, ff -40 C with 3.6 V, sf -40 C with 3.6 V and fs 125 C with 3.0 V. The switch current sets the loop gain, and these span the weakest switch (ss hot, low input), the strongest (fast PMOS cold, high input) and the comparators' slow and fast NMOS against the opposite switch. The 1.2 V logic supply (comparators, controller, shifter inputs) is an ideal 1.2 V source in every run, since that is vdd_mem's own setpoint; the ladder and divider are ratios of identical rppd units, so they stay at the typical resistor corner.

Real-number loop model: the switch array and comparators are replaced by the measured unit current against rail and input voltage, the measured unit delay and ideal clocked comparators, around the same controller RTL, decoupling, divider, ladder and load. Error metric, fixed before fitting: per setpoint, the mean rail, the ripple and the lowest and highest rail, and per DVFS change the transition time, model against the transistor loop. Allowed error: 3 mV on the mean, 5 mV on the ripple, 10 mV on the lowest and highest rail, 40 ns (two clocks) on a transition. It is fitted on the tt run at the design gains and validated on the other corners and on the high-gain broken copy.


See the table in `plan.md`. In short:
- Half an LSB of settling in 200 ns needs tau under 32 ns. Gain -1 halves the loop bandwidth, so GBW must be at least 20 MHz for tau = 16 ns.
- A 0.4 V swing needs 60.2 dB for a quarter-LSB static error. 66 dB leaves room for the slow corners.
- A 64-sample frame every 64 us is 3200 cycles at 50 MHz, which is the filter's budget.
