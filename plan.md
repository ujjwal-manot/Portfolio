# EdgeSense-130 plan

Updated 21 Nov 2026.

## What this is

A chip design lab on the free IHP 130 nm process (SG13G2, 1.2 V), using the open source tools in the `hpretl/iic-osic-tools:2026.10` Docker image plus a short list of pinned extras. It has four core projects, an end-to-end chip run, and seven flagship projects. Each one is designed, tested with real simulators, signed off the way a product team would, and checked against broken copies of itself to prove the tests are not lying.

Everything is built in the open. Every design is visible at any time.

## The chip

```
sensor (0.2 to 1.0 V, up to 50 kHz)
  -> opamp        inverting amplifier, gain -1 around 0.6 V, drives the ADC
  -> adc          8-bit SAR ADC, 1 MS/s, 10 MHz clock (2 cycles sample, 8 cycles convert)
  -> fifo_bridge  16-deep async FIFO + AXI4-Stream skid buffer, 10 MHz -> 50 MHz
  -> cpu          5-stage RV32I with forwarding, hazard unit, 2-bit branch predictor
flagships (digital)  tensor_core, coherent_cache, noc, cpu_plus
flagships (analog)   serdes, power, adc_10bit
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

- PDK: `/foss/pdks/ihp-sg13g2`, models `cornerMOSlv.lib` + PSP103 OSDI, standard cells at slow (1.08 V, 125 C), typical (1.2 V, 25 C) and fast (1.32 V, -40 C), IHP SRAM macros (`RM_IHPSG13_1P_*`), layer colours in `sg13g2.lyp`
- Tools: ngspice 47, Xyce 7.10, Icarus 14.0-devel, Verilator 5.052, Yosys 0.70, SBY 0.70, eqy 0.70, OpenROAD 26Q4, OpenSTA 3.1.0, LibreLane 3.1.0.dev3, Magic 8.3.685, KLayout 0.30.12, Netgen 1.5.324, Xschem 3.4.8RC, cocotb 2.1.0, pyuvm 5.0.0, Fault 0.9.4, FuseSoC 2.4.7, opencdc, Verible, slang, scikit-rf 2.1.0, numpy 2.5.4, scipy 1.18.1, matplotlib 3.11.2, riscv64-unknown-elf-gcc 16.1.0, Spike, Node 18
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
7. Python only reads simulator output. It never simulates circuits itself. The instruction and number-format reference models are the exception, and each is checked against an outside reference (Spike, SoftFloat/TestFloat).
8. Real IHP models only. No toy `.model` lines, no "pretend it passed if the tool is missing". Missing tools stop the run with an error.
9. Every test suite must catch three deliberately broken copies of its own design.
10. Depth over breadth: two flagships taken all the way to signed-off layout beat seven left at simulation.

## Folders

```
README.md            what this is and how to run it
plan.md              this file
chip.md              whole-chip spec
Makefile             make check_tools | make tools | make all | make compare | make honesty | make console
setup/               start_tools.sh, run.sh, check_tools.sh, get_tools.sh, tool_versions.txt
helpers/             save_result.py, check_honesty.py, cocotb_run.py, cpu_model.py, cdc_check.py, transistor_charts.py,
                     opamp_sizing.py, opamp_results.py, adc_spectrum.py, mtbf.py, number_formats.py, eye_diagram.py
projects/
  fifo_bridge/       async FIFO + skid buffer
  cpu/               5-stage RV32I
  opamp/             two-stage Miller opamp, schematic + layout
  adc/               8-bit SAR ADC
  whole_chip/        adc -> fifo_bridge -> cpu running the filter, end to end
  tensor_core/       8x8 mixed-precision systolic array
  coherent_cache/    2 to 4 cores, MESI, shared L2
  noc/               2D mesh network and a die-to-die link
  cpu_plus/          2-wide RV32IMC core
  serdes/            PLL, transmitter, equalizers, clock recovery
  power/             bandgap, LDO, digital LDO with DVFS
  adc_10bit/         10-bit SAR ADC
compare_with_papers/ transistors/, ota_5t/, cummings_fifo/, reference_block/, report.md
console/             read-only viewer: schematics, layouts, waveforms, results, 3D die
hardware/            stm32_dac/, tang_nano/
tracking/            log_session.py, scorecard.md, decide.py
```

Every project folder looks the same, so it can be copied out as its own repo:

```
README.md     spec, block diagram, results table, design review, interview questions, things to try
design/       the design
tests/        testbenches
formal/       formal checks (digital)
timing/       synthesis, timing, power, equivalence and test scripts (digital)
broken/       three small patches that break the design on purpose
results/      summary.json + raw logs
Makefile      make test | formal | timing | broken | layout | all, where each applies
```

## Signoff checks for every digital block

Each digital block (fifo_bridge, cpu, every digital flagship) gets these, each with its log in `results/`:

| Check | Tool | Pass rule |
|---|---|---|
| Timing at three corners | Yosys mapping (with ABC buffering and sizing), OpenSTA on the slow, typical and fast IHP libraries | no negative setup slack at slow, no negative hold slack at fast |
| Power | OpenSTA with switching activity read from a VCD written by the cocotb run | number reported per corner, with the activity source named |
| Clock and reset crossings | `cdc_check.py` on the Yosys netlist, a formal proof that each Gray pointer changes at most one bit per cycle, and opencdc as a second opinion | every crossing lands on a two-flop chain with no logic in front of it, multi-bit crossings are proved Gray, every reset is released through a reset synchronizer; probe designs show what each checker catches and misses |
| RTL vs netlist | eqy | equivalent |
| Scan and test patterns | Fault: scan chain insertion, ATPG, coverage report | on cpu at least; coverage reported, not hidden |
| Layout (where it applies) | LibreLane to GDS, KLayout DRC, Netgen LVS, OpenROAD timing after routing | clean, or the failures listed |

Each README has a short design review: what was tried, what failed, the numbers, and why the final choice won.

## Core projects

The four core blocks are small on purpose, but each one is taken past the textbook version to the questions a product team actually asks: will it fail in silicon, how do we know, what did it cost, and what was the alternative.

### fifo_bridge: a clock-crossing block you could ship
- Design: Gray-code async FIFO (16 deep, 8 data bits + last), skid buffer with a registered `tready`, top-level bridge.
- Reset crossing done right: each side gets a reset synchronizer (asserts at once, releases on its own clock), and a reset on either side clears both pointers safely. This is the problem the clock-crossing tool flags on the plain textbook FIFO.
- Metastability injection: the two-flop synchronizer has a simulation mode that randomly makes each captured bit resolve to the old or the new value, the way a real flop can. The cocotb traffic must still lose nothing. A copy that sends a binary pointer instead of Gray passes plain simulation but must fail under injection, which shows why the tests need it.
- Synchronizer MTBF from transistor physics: ngspice sweeps data-to-clock timing on the real IHP flop netlist from the standard-cell library, `mtbf.py` fits the resolution time constant tau and the window T0 from the ngspice output, and the report gives MTBF for 2 and 3 flops at 10 and 50 MHz at each corner.
- Tests: cocotb random traffic in both clock directions, 80k+ words, zero loss, duplication or reordering, AXI stability while stalled, and checks that the FIFO really filled and emptied.
- Formal: full proofs (PDR) of the FIFO and the skid buffer, a 40-step bounded check of the joined bridge, and covers proving each rule is reached (the deepest at step 32).
- Signoff: clock and reset crossing check with `cdc_check.py` on the netlist (each rule proved by a bad probe design it must catch), the formal Gray proof, and opencdc 0.4.1 as a second opinion with its measured blind spots written down (it misses crossings inside generate blocks and rejects multi-bit two-flop chains), a skew limit on the Gray bus in the timing constraints (bits must arrive within one destination period of each other), three-corner timing, power from simulation activity, eqy.
- Depth sizing: the README works out the minimum depth for a given burst length and clock ratio, and the tests show the measured limit matches it.
- Broken copies: drop the word at the end of each memory lap, full check that inverts only the top Gray bit, output data that changes while stalled, and (under injection) a binary pointer crossing.

### cpu: a core verified against the ISA, not just a few tests
- Design: 5-stage RV32I with forwarding, load-use stall, branch flush, 2-bit predictor with a 16-entry BTB, performance counters, memory-mapped stream input.
- Machine mode: Zicsr, traps (illegal instruction, ecall, misaligned), timer and external interrupts, `wfi`. The filter firmware sleeps until a frame is ready instead of polling, and the power saving is measured.
- Formal ISA check: an RVFI port and riscv-formal, so every instruction is proved against the RISC-V spec, plus its register, PC, causality and liveness checks.
- Random programs: riscv-dv (its Python generator) writes random instruction streams, run in lockstep against the reference model, which is itself checked against Spike.
- Compliance: rv32ui riscv-tests and riscv-arch-test.
- Hardware and software together: one custom instruction (a multiply-accumulate on the custom-0 opcode) for the FIR. Measured cycles per frame and area, with and without it.
- Measured trade-offs: CoreMark per MHz; BTB size (0, 4, 16, 64) against mispredictions and area; forwarding on and off against CPI.
- Physical: LibreLane to GDS with IHP SRAM macros (1024 x 32) as instruction and data memory, full signoff checks, Fault scan insertion and ATPG coverage.
- On a board: CoreMark and the filter on the Tang Nano 20K, results over UART.
- Broken copies: no forwarding from MEM, missing load-use stall, no flush after a mispredict.

### opamp: a sizing method you can trust, checked in its real load
- Design: two-stage Miller opamp with a nulling resistor, plus layout with a common-centroid input pair, interdigitated mirrors and guard rings.
- Sizing method: ngspice sweeps the real IHP transistors into gm/Id tables; `opamp_sizing.py` picks every W and L from the tables and the spec by arithmetic alone; ngspice then checks the result. The README reports predicted vs simulated values, so the method itself is tested.
- In its real load: besides an ideal 2.05 pF cap, it is simulated driving the ADC's sampling switch and capacitor DAC, with the comparator's kickback.
- Full spec set: gain, GBW, phase margin (Tian, in the real loop), slew, settling to half an LSB, output swing, input noise integrated over the ADC bandwidth against kT/C and the LSB, PSRR, CMRR, power.
- Yield: corners (TT/SS/FF/SF/FS x temperature x supply +-10%) and 1000 Monte Carlo runs, giving the yield per spec, the combined yield and the worst corner.
- Layout: DRC and LVS clean, extraction with Magic, pre- vs post-layout table.
- A design-review comparison: Miller with a nulling resistor against indirect (cascode) compensation, measured settling, power and area.
- An ideal two-pole model runs through the same scripts, to prove the measurement scripts are right.
- Broken copies: phase margin under 20 deg, GBW/slew below spec, gain under 45 dB.

### adc: an architecture choice backed by energy numbers
- Architecture study: conventional, monotonic and Vcm-based capacitor switching, compared on energy per conversion (from ngspice supply current), DAC area and linearity. The winner is chosen by those numbers.
- Timing: asynchronous (self-timed) SAR logic against the 10 MHz synchronous version, compared on power, the clock it needs and the metastability rate.
- Comparator: StrongARM latch; offset from Monte Carlo, noise from transient noise, kickback, and decision time vs input.
- Full transistor-level FFT: coherent sine input, 128 points in quick mode and 1024 in full mode; ENOB, SNDR and SFDR at every corner; histogram DNL/INL; offset and gain error.
- Where it stands: Walden and Schreier figures of merit, plotted on Murmann's published ADC survey (pinned revision) next to real published converters.
- Layout: common-centroid MIM capacitor array and comparator, DRC/LVS clean, post-layout ENOB.
- A real-number model fitted to the transistor results drives `whole_chip`.
- An ideal 8-bit quantizer, run in Verilator, must score ENOB 8.0 +- 0.1.
- Broken copies: +2 LSB comparator offset, 10% MSB cap mismatch, non-coherent test tone.

### whole_chip
- The ADC model feeds the bridge, which feeds the cpu running the filter firmware, all in one Verilator run.
- Checks: frames arrive intact, no overflow, the filter meets its cycle budget, the cpu sleeps between frames.

### Continuous checking
- A GitHub Actions workflow pulls the same image and runs the quick checks (unit tests, formal covers, broken copies, honesty check) on every push. The slow transistor runs stay local.

## Flagship projects

Researched against current new-grad and junior postings at NVIDIA, AMD, Tesla and Intel. The common asks are: microarchitecture plus RTL, SystemVerilog/UVM and formal, computer arithmetic and low-precision formats, interconnects and caches, the full flow through synthesis and timing, and measured trade-offs instead of claims. Each flagship is built to hit several of these at once.

Two flagships go all the way to signed-off layout; `tracking/decide.py` picks which, once the core projects and your scorecards are done. Digital: tensor_core and coherent_cache go all the way to signed-off layout, noc and cpu_plus to formal and simulation. Analog: serdes and power go all the way to post-layout corners, adc_10bit to post-layout ENOB.

### tensor_core (digital 1)
- Design: 8x8 systolic array of fused multiply-add cells. Inputs BF16, FP8 E4M3 and E5M2, and OCP MX block formats (MXFP8 and MXFP4 with a shared E8M0 scale per 32 elements). FP32 accumulate, round to nearest even.
- Reference: FP8 and BF16 products are exact in FP32, so SoftFloat's `f32_mulAdd` on the widened inputs is a bit-exact reference for every cell. All 256 FP8 codes are checked exhaustively in both formats. TestFloat runs the FP32 adder.
- Dataflow study: weight-stationary vs output-stationary, both built, measured utilization on a real convolution layer and a GEMM, and a roofline write-up with the measured points on it.
- Performance model: a cycle model in Python whose cycle counts must match the RTL within 2% on every workload.
- Accuracy study: one real network layer in BF16, FP8 and MXFP4 against an FP32 run, error reported.
- Layout: LibreLane to GDS, full signoff checks. A 4x4 version sized for a Tiny Tapeout IHP tile, prepared for the next IHP shuttle once its dates are announced; submitting costs money and is your call at that point.
- Broken copies: rounding toward zero, FP8 subnormals flushed to zero, block scale applied one element late.

### coherent_cache (digital 2)
- Design: 2 to 4 of our RV32I cores, private L1s, MESI coherence on a snooping bus, shared L2 built from IHP SRAM macros.
- Verification: UVM testbench (Accellera UVM 2020.3.1 on Verilator, pyuvm if that does not hold up) with constrained random traffic, scoreboard and coverage closure reports. Formal proofs of the coherence rules: at most one writer, and every reader sees the last write. Memory-ordering litmus tests run on the cores.
- Measured: miss rate and average latency on CoreMark and Embench, for 1, 2 and 4 cores.
- Layout: LibreLane to GDS with the SRAM macros placed, full signoff checks.
- Broken copies: a missed invalidate, a dirty line dropped on eviction, a lost upgrade race.

### noc (digital 3)
- Design: 2D mesh routers with credit flow control and virtual channels, dimension-order routing, plus a die-to-die link (flits with CRC and a replay buffer) so two halves of the mesh can sit on separate dies.
- Formal: deadlock freedom, no flit lost or duplicated, and replay delivering every flit exactly once under injected bit errors.
- Measured: latency vs injection rate under uniform, hotspot and transpose traffic.
- It ties the cores and the tensor_core into one SoC.
- Broken copies: credit returned one cycle early, a routing turn that allows a cycle, replay that skips one flit.

### cpu_plus (digital 4)
- Design: the 5-stage core grown into a 2-wide in-order superscalar with the M and C extensions and a gshare predictor, then a small TAGE, each kept if the numbers justify it.
- Tests: the same Spike lockstep, rv32ui/um/uc riscv-tests, and riscv-arch-test.
- Measured: IPC, stall breakdown and branch mispredictions per thousand instructions on CoreMark and Embench, before and after each change.
- Broken copies: two dependent instructions issued together, a compressed instruction split across a fetch boundary, a predictor history not restored after a flush.

### serdes (analog 1)
- Design: charge-pump PLL, CML serializer and driver using the process's SiGe HBTs, CTLE, 1-tap DFE, bang-bang clock recovery.
- Tests: PLL jitter budget from transient noise; eye diagrams through a lossy channel built from SPICE transmission-line elements, at a few Gb/s; bit error count on PRBS7 and PRBS31.
- `eye_diagram.py` only folds ngspice output into an eye; the channel and circuits run in ngspice.
- Layout of the driver and CTLE, post-layout eye.
- Broken copies: CTLE zero misplaced, DFE tap with the wrong sign, CDR loop gain too high.

### power (analog 2)
- Design: bandgap reference, capless LDO, and a digital LDO controller with DVFS states the cpu sets through a register.
- Tests: temperature coefficient, PSRR, line and load regulation, load step, corners and Monte Carlo; DVFS state changes driven by firmware.
- Layout with post-layout corners.
- Broken copies: bandgap start-up removed, LDO compensation cap too small, DVFS step without settling time.

### adc_10bit (analog 3)
- Design: extends the adc with a bootstrapped switch, segmented DAC and calibration.
- Results: post-layout ENOB.
- Broken copies: bootstrap cap too small, calibration disabled, segment decoder off by one.

## Comparing with published work

`make compare` writes `compare_with_papers/report.md`, with our value, the published value, the exact source and the difference:

- IHP transistor threshold, current and gm/Id, against IHP's own `SG13G2_os_process_spec.pdf` (only numbers that are actually in it)
- JKU 5-transistor OTA from the IHP tutorial: simulation, DRC, LVS
- Cummings SNUG-2002 async FIFO: formal + cocotb on the original, fails when one line is broken
- The LibreLane reference block bundled with the PDK: cells, area, fmax

Where no published number exists, the report says so.

## Console

`make console` opens a read-only viewer in the style of a professional layout and schematic tool (Vite + React + three.js + uPlot). It never edits anything, and it uses no product names, logos, icons or dialogs from any vendor; every icon is drawn for this project.

- **Shell:**
  - Library tree on the left: one entry per block, with its views (schematic, layout, waveforms, results, 3D die).
  - Layer palette on the right, filled from the IHP SG13G2 KLayout `.lyp` file: real layer names, colours and stipple patterns, each with a visibility toggle.
  - Command log at the bottom: every file the viewer loaded, with its SHA-256 from `summary.json`.
  - Status bar: cursor X/Y in um, zoom, the open cell, and the result of the open block.
  - Black canvas with a dot grid.
- **Schematic view:** the xschem SVG export of each schematic, with pan and zoom.
- **Waveform view:** black background, coloured traces, two click cursors with delta readout. Data comes straight from the real ngspice `.raw` files, parsed in the browser.
- **Layout view:** the GDS exported by a KLayout script, drawn with the PDK's layer colours and stipples.
- **3D die view:** the die on its package, one tile per block coloured by result (grey not run, green pass, red fail). Signal particles flow only through passing blocks. Click a tile to open its layout.
- **Results view:** each check with its log and hash, the broken-copy table, the comparison table, and plots from the logs (Bode, step response, FFT, DNL/INL, gm/Id, IPC, timing slack).
- **Decision view:** digital vs analog totals from your scorecards, with the 15% rule from your career report.
- **Open in xschem / KLayout:** buttons that show the exact shell command to open the same file in the real tool. The viewer does not run it.
- **Reliability:** it only shows data read from `results/`. A block with no `summary.json` shows as "not run". A reduced-motion switch turns off camera moves and particles.

## Hardware

- **stm32_dac:** 8-bit R-2R DAC on a breadboard, driven and measured by the Nucleo-H753. `adc_spectrum.py` computes DNL/INL/ENOB from the measured data.
- **tang_nano:** fifo_bridge and cpu on a Tang Nano 20K (Gowin GW2AR-18), results over UART. Open-source flow: Yosys + nextpnr-himbaechel + apicula + openFPGALoader.

## Tools

Tools already in `iic-osic-tools:2026.10` are used as the image ships them. Everything else is fetched by `make tools` (`setup/get_tools.sh`) into `third_party/` or `build/`, never committed, at the exact version below. `setup/check_tools.sh` checks every one and fails if any is missing.

| Need | Tool | Version |
|---|---|---|
| UVM | Accellera UVM-SV (`accellera-official/uvm-core`) | tag 2020.3.1 |
| Solvers | Bitwuzla | 0.8.2 |
| | Boolector | 3.2.4 |
| Equivalence | eqy | image (0.70) |
| Scan and test patterns | Fault | image (0.9.4) |
| SRAM | IHP SRAM macros `RM_IHPSG13_1P_*` | image PDK |
| ISA formal | riscv-formal | c992aa61fdfe |
| Random programs | riscv-dv | f557b89ed688 |
| ADC comparison | Murmann ADC survey | 00b4b855de5c (rev20260801) |
| Clock crossings | opencdc | image |
| CPU tests | riscv-tests | 3df703cd52d5 |
| | riscv-arch-test | tag 3.10.0 |
| | CoreMark (`eembc/coremark`) | 1f483d5b8316 |
| | Embench IoT | 09c2ed8c3b70 |
| Packaging | FuseSoC | image (2.4.7) |
| Tiny Tapeout | tt-support-tools | 0922544e6c7f |
| Tang Nano 20K | nextpnr (himbaechel, Gowin) | tag nextpnr-0.11.1 |
| | apicula | 0.35 |
| | openFPGALoader | tag v1.2.0 |
| STM32 | arm-none-eabi-gcc (Arm GNU Toolchain) | 14.3.rel1 |
| | libopencm3 | a3977e14519e |
| | OpenOCD | tag v0.12.0 |
| SerDes | scikit-rf | image (2.1.0) |
| | PyBERT, as a cross-check of `eye_diagram.py` | tag v11.2.0 |
| Python | numpy, scipy (FFT and filters only), matplotlib | image |
| Console | Node LTS | 24.11.1 |
| | Vite, React, three.js, uPlot | pinned in `console/package-lock.json` |
| Number formats | Berkeley SoftFloat 3 | 07ebd29db0cf |
| | Berkeley TestFloat 3 | a9c849f1b0eb |

## Using it for your branch decision

Each project README ends with "things to try": three changes to make yourself, for example a 32-deep FIFO, a 100 MHz opamp, or a 3-bit predictor. Do them in the order fifo_bridge, opamp, cpu, adc, logging each session with `tracking/log_session.py`. Fill `tracking/scorecard.md` after each project. `tracking/decide.py` applies your report's rules: the 15% margin, a tie goes digital, and opamp energy of 2 or less rules out analog. Its answer picks which flagships go all the way.

## Build order

Every file is tested as soon as it exists. A step is finished when all of its files pass, its three broken copies are caught, the honesty check passes, and it is committed.

1. setup, helpers, `check_honesty.py` (and a test that it catches planted cheats), tracking, `chip.md`
2. fifo_bridge, with signoff checks
3. cpu, with signoff checks and layout
4. `make tools`: fetch and check every pinned extra
5. transistor charts, then opamp
6. adc
7. whole_chip
8. console
9. compare_with_papers
10. tensor_core
11. coherent_cache
12. noc
13. cpu_plus
14. serdes
15. power
16. adc_10bit
17. hardware
18. confirm a fresh clone reproduces every result (a check that the setup is complete, not a bug hunt)

Steps 10 to 16 follow the track `decide.py` picks: its two main flagships go first and all the way; the others follow at the depth given above.

## Risks

- VCS, Xcelium and Spectre targets cannot be tested here.
- Some published numbers may not exist in the IHP documents. The report will say so.
- Verilator runs most but not all of UVM; pyuvm is the fallback.
- 8x8 may not fit a Tiny Tapeout tile; 4x4 is the fallback.
- Open tools have no UPF power-intent flow, so multi-voltage checks for the power project are done by simulation, and that limit is stated.
- The full bridge proof did not finish in 20 minutes; it is split into full proofs of each half plus a bounded check of the whole.
- Analog layout done by script is the hardest part. If a layout cannot be made DRC/LVS clean, it gets reported, not hidden.
- SerDes, PLL and full-ADC transistor simulations are slow; each has a quick mode and a full mode.
- This cloud machine is wiped between sessions. Everything is committed as it goes, and `setup/start_tools.sh` plus `make tools` rebuild the tools.
