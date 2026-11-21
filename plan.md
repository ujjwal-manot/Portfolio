# EdgeSense-130 plan

Updated 21 Nov 2026.

## What this is

A chip design lab on the free IHP 130 nm process (SG13G2, 1.2 V), using the open source tools in the `hpretl/iic-osic-tools:2026.10` Docker image. It holds nine complete projects. Each one is designed, tested with real simulators, and checked against broken copies of itself to prove the tests are not lying.

Everything is built now. Every design is visible at any time.

## The chip

```
sensor (0.2 to 1.0 V, up to 50 kHz)
  -> opamp        inverting amplifier, gain -1 around 0.6 V, drives the ADC
  -> adc          8-bit SAR ADC, 1 MS/s, 10 MHz clock (2 cycles sample, 8 cycles convert)
  -> fifo_bridge  16-deep async FIFO + AXI4-Stream skid buffer, 10 MHz -> 50 MHz
  -> cpu          5-stage RV32I with forwarding, hazard unit, 2-bit branch predictor
  -> accelerator / cache   (digital extensions)
     adc_10bit / regulator / pll   (analog extensions)
```

### Why the numbers are what they are

| Item | Working | Value |
|---|---|---|
| 1 LSB | 0.8 V / 256 | 3.125 mV |
| Ideal 8-bit SNR | 6.02 x 8 + 1.76 | 49.9 dB (ENOB 8.0) |
| Sampling cap | 256 x 8 fF | 2.05 pF |
| Its kT/C noise | sqrt(kT/C), 300 K | 45 uV, far below quantization noise (0.9 mV) |
| Settling | 0.8 V step to half an LSB in 200 ns needs ln(512) = 6.24 time constants | tau must be under 32 ns, target 16 ns |
| Opamp bandwidth | gain -1 gives beta = 0.5, tau = 1/(2 pi beta GBW) | GBW >= 20 MHz gives 15.9 ns |
| Opamp DC gain | output swings +-0.4 V around 0.6 V, error 0.4 x 2/A under 0.78 mV | 60.2 dB minimum, target 66 dB for corner margin |
| Slew rate | most of 200 ns left for fine settling | >= 10 V/us |
| Phase margin | measured in the real beta = 0.5 loop (Tian), every corner and Monte Carlo | >= 60 deg |
| CPU clock | system clock | 50 MHz at slow corner (1.08 V, 125 C) |
| CPU workload | a 64-sample frame every 64 us is 3200 cycles | 8-tap FIR + threshold under 3200 cycles per frame |
| FIFO depth | 16 entries at 1 us each | CPU can pause 16 us without losing data |

Why the opamp is inverting: in a unity-gain buffer, the opamp inputs would have to follow the signal from 0.2 V to 1.0 V. Measured thresholds (below) say a PMOS input pair stops working near 0.6 V and an NMOS pair below about 0.45 V. In the inverting setup the inputs stay at 0.6 V, so a normal two-stage Miller opamp works. The CPU undoes the flip with `code ^ 0xFF`.

The targets of 66 dB, 50 MHz and 3200 cycles are my own picks. If a real design cannot reach one, I relax it and write down why.

## Measured on this setup

Inside `iic-osic-tools:2026.10`, 21 Nov 2026:

- PDK: `/foss/pdks/ihp-sg13g2`, models `cornerMOSlv.lib` + PSP103 OSDI
- Tools: ngspice 47, Xyce 7.10, Icarus 14.0-devel, Verilator 5.052, Yosys 0.70, SBY 0.70, OpenROAD 26Q4, OpenSTA 3.1.0, LibreLane 3.1.0.dev3, Magic 8.3.685, KLayout 0.30.12, Netgen 1.5.324, Xschem 3.4.8RC, cocotb 2.1.0, pyuvm 5.0.0, riscv64-unknown-elf-gcc 16.1.0, Spike
- Missing: Gowin FPGA tools for the Tang Nano, and UVM source for Verilator. Both get installed when needed, with pinned versions.
- NMOS threshold (TT, 27 C): 0.40 V at L = 0.13 um, 0.23 V at 0.5 um, 0.20 V at 1 um
- PMOS threshold: -0.41 V, -0.36 V, -0.35 V at the same lengths
- NMOS current at W = 1 um, L = 0.13 um, Vgs = Vds = 1.2 V: 400.5 uA

## Rules

1. Smallest code that fully works. No wrappers, options or "for later" code.
2. Each file gets exactly one comment line, at the top, saying what the file is. No other comments.
3. Plain names for every folder and file (`opamp`, `adc_spectrum.py`, `broken`).
4. Test every file the moment it is written, never in a batch at the end. For a design file, write its test first, run it and watch it fail, then build until it passes. A file is not done until its test passes.
5. No claim without proof. A result counts only if the real tool's log is on disk and its SHA-256 matches the one in `results/summary.json`.
6. Find the root cause of a failure before changing anything.
7. Python only reads simulator output. It never simulates circuits or logic itself (the CPU and accelerator reference models are the one exception, and they are checked against Spike and NumPy).
8. Real IHP models only. No toy `.model` lines, no "pretend it passed if the tool is missing". Missing tools stop the run with an error.
9. Every test suite must catch three deliberately broken copies of its own design.

## Folders

```
README.md            what this is and how to run it
plan.md              this file
chip.md              whole-chip spec
Makefile             make check_tools | make all | make compare | make honesty | make console
setup/               start_tools.sh, run.sh (runs a command inside the tool image), check_tools.sh
helpers/             transistor_charts.py, opamp_results.py, adc_spectrum.py, cpu_model.py,
                     accelerator_model.py, save_result.py, check_honesty.py
projects/
  fifo_bridge/       async FIFO + skid buffer
  opamp/             two-stage Miller opamp, schematic + layout
  cpu/               5-stage RV32I
  adc/               8-bit SAR ADC
  whole_chip/        adc -> fifo_bridge -> cpu running the filter, end to end
  accelerator/       8x8 INT8 systolic array, Tiny Tapeout version
  cache/             write-back L1 cache + UVM testbench
  adc_10bit/         10-bit SAR ADC
  regulator/         bandgap + capless LDO
  pll/               charge-pump PLL
compare_with_papers/ transistors/, ota_5t/, cummings_fifo/, reference_block/, report.md
console/             3D web app
hardware/            stm32_dac/, tang_nano/
tracking/            log_session.py, scorecard.md, decide.py
```

Every project folder looks the same, so it can be copied out as its own repo:

```
README.md     spec, block diagram, results table, interview questions, things to try
design/       the design
tests/        testbenches, formal checks, timing scripts
broken/       three small patches that break the design on purpose
results/      summary.json + raw logs
Makefile      make test | make broken | make layout (where it applies)
```

## Projects

### fifo_bridge
- Design: Gray-code async FIFO (16 deep, 9 bits = 8 data + last), skid buffer with a registered `tready`, top-level bridge.
- Tests: cocotb random traffic in both clock directions (fast to slow, slow to fast), 100k+ words, zero loss, duplication or reordering, and a check that data really flowed.
- Formal: SymbiYosys proof of no overflow or underflow, data integrity, and AXI handshake rules.
- Timing: Yosys + OpenSTA with async clock groups.
- `SIM=vcs` and `SIM=xcelium` targets are written but untested (no licence).
- Broken copies: drop a byte on wrap, bad pointer sync, skid stall one cycle late.

### opamp
- Design: two-stage Miller opamp sized from gm/Id charts, plus layout.
- Tests:
  - DC operating point.
  - Open-loop gain and GBW.
  - Closed loop at gain -1 into 2.05 pF: Tian phase margin, settling, slew.
  - Corners TT/SS/FF/SF/FS x temperature x supply +-10%, and 200 Monte Carlo runs.
- Layout: KLayout DRC clean, Netgen LVS clean, post-layout extraction re-checked against the specs.
- Broken copies: phase margin under 20 deg, GBW/slew below spec, gain under 45 dB.
- An ideal two-pole model also runs through the same scripts, to prove the measurement scripts are right.

### cpu
- Design: 5-stage RV32I with forwarding, load-use stall, branch flush, 2-bit branch predictor with BTB, performance counters, memory-mapped stream input.
- Tests:
  - Official `rv32ui` riscv-tests, with every retired instruction checked in lockstep against `cpu_model.py`, which is itself checked against Spike.
  - The filter benchmark, timed with the CPU's own counters.
- The riscv-tests use a minimal environment, since plain RV32I has no CSRs.
- Layout: LibreLane RTL to GDS on IHP. Report area, fmax and power.
- Broken copies: bad EX-to-EX forwarding, missing load-use bubble, wrong flush on a taken branch.

### adc
- Design: StrongARM comparator and binary capacitor DAC at transistor level, SAR logic + 64-sample framing in SystemVerilog, real-number model.
- Tests:
  - Comparator delay, offset and noise.
  - DAC settling.
  - SAR logic in Verilator.
  - Mixed ngspice + digital simulation.
  - Coherent FFT: ENOB, SNDR, SFDR. Histogram DNL/INL. Offset and gain error.
- An ideal 8-bit quantizer, run in Verilator, must score ENOB 8.0 +- 0.1.
- Broken copies: +2 LSB comparator offset, 10% MSB cap mismatch, non-coherent test tone.

### whole_chip
- The ADC model feeds the bridge, which feeds the CPU running the filter firmware, all in one Verilator run.
- Checks: frames arrive intact, no overflow, the filter meets its cycle budget.

### accelerator
- Design: 8x8 INT8 systolic array, AXI4-Stream, ping-pong buffers, clock gating.
- Tests: results compared with a NumPy model; throughput.
- Layout: LibreLane with power. A Tiny Tapeout IHP version is added; it drops to 4x4 if 8x8 does not fit the tile.

### cache
- Design: write-back L1 cache.
- Tests: UVM testbench with constrained random traffic, scoreboard, assertions and coverage. It runs on Verilator + Accellera UVM if that works on 5.052, otherwise on pyuvm.

### adc_10bit
- Design: extends the adc with a bootstrapped switch, segmented DAC and calibration.
- Results: post-layout ENOB.

### regulator
- Design: bandgap + capless LDO.
- Tests: temperature coefficient, PSRR, line and load regulation, load step.

### pll
- Design: charge-pump PLL.
- Tests: lock time, jitter, phase noise. These are slow simulations, so there is a quick mode and a full mode.

## Comparing with published work

`make compare` writes `compare_with_papers/report.md`, with our value, the published value, the exact source and the difference:

- IHP transistor threshold, current and gm/Id, against IHP's own `SG13G2_os_process_spec.pdf` (only numbers that are actually in it)
- JKU 5-transistor OTA from the IHP tutorial: simulation, DRC, LVS
- Cummings SNUG-2002 async FIFO: formal + cocotb on the original, fails when one line is broken
- The LibreLane reference block bundled with the PDK: cells, area, fmax

Where no published number exists, the report says so.

## 3D console

`make console` opens a web app (Vite + React + three.js + uPlot):

- **The chip in 3D:** a die on its package. Each project is a tile coloured by its latest result: grey not run, green passing, red failing.
- **Signal path:** particles flow sensor -> opamp -> adc -> fifo_bridge -> cpu, but only through blocks that pass.
- **Layouts:** click a tile to fly into its real layout, built from the GDS by a KLayout script, with IHP metal layers stacked in 3D.
- **Side panel:**
  - Results with log hashes.
  - Plots from the real logs: Bode, step response, FFT, DNL/INL, gm/Id, IPC, timing slack.
  - The broken-copy table.
  - The comparison table.
- **Decision view:** digital vs analog totals from your scorecards, with the 15% rule from your career report.
- **Reliability:** it only shows data read from `results/`. Missing data shows as "not run". There's a 2D list view for slow laptops and a reduced-motion switch.

## Hardware

- **stm32_dac:** 8-bit R-2R DAC on a breadboard, driven and measured by the Nucleo-H753. `adc_spectrum.py` computes DNL/INL/ENOB from the measured data.
- **tang_nano:** fifo_bridge and cpu on a Tang Nano 20K (Gowin GW2AR-18), results over UART. Open-source flow: Yosys + nextpnr-himbaechel + apicula + openFPGALoader.

## Using it for your branch decision

Each project README ends with "things to try": three changes to make yourself, for example a 32-deep FIFO, a 100 MHz opamp, or a 3-bit predictor. Do them in the order fifo_bridge, opamp, cpu, adc, logging each session with `tracking/log_session.py`. Fill `tracking/scorecard.md` after each project. `tracking/decide.py` applies your report's rules: the 15% margin, a tie goes digital, and opamp energy of 2 or less rules out analog.

## Build order

Every file is tested as soon as it exists. A step is finished when all of its files pass, its three broken copies are caught, the honesty check passes, and it is committed.

1. setup, helpers, `check_honesty.py` (and a test that it catches planted cheats), tracking, `chip.md`
2. fifo_bridge
3. cpu
4. transistor charts, then opamp
5. adc
6. whole_chip
7. compare_with_papers
8. console
9. accelerator
10. cache
11. adc_10bit
12. regulator
13. pll
14. hardware
15. confirm a fresh clone reproduces every result (a check that the setup is complete, not a bug hunt)

## Risks

- VCS, Xcelium and Spectre targets cannot be tested here.
- Some published numbers may not exist in the IHP documents. The report will say so.
- UVM on Verilator may not work; pyuvm is the fallback.
- 8x8 may not fit a Tiny Tapeout tile; 4x4 is the fallback.
- Analog layout done by script is the hardest part. If a layout cannot be made DRC/LVS clean, it gets reported, not hidden.
- PLL and full-ADC transistor simulations are slow.
- This cloud machine is wiped between sessions. Everything is committed as it goes, and `setup/start_tools.sh` rebuilds the tools.
