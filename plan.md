# EdgeSense-130 plan

Updated 21 Nov 2026. Final.

## What this is

A chip design lab on the free IHP 130 nm SiGe BiCMOS process (SG13G2), built with the open source tools in the `hpretl/iic-osic-tools:2026.10` Docker image plus a short list of pinned extras.

The work is split into three equal tracks, one third of the effort each:

| Digital VLSI | Analog VLSI | Analog/mixed-signal (AMS) |
|---|---|---|
| fifo_bridge | opamp | adc |
| cpu | bandgap_ldo | power_manager |
| tensor_core | serdes_frontend | serdes_link |
| coherent_noc | lc_vco | frac_n_pll |

Each track has two core projects and two flagships. `whole_chip` joins the core blocks of all three tracks into one mixed-signal chip.

The goal is work that holds up in a hiring loop at NVIDIA, AMD, Intel, Tesla, Apple, Qualcomm, Broadcom, Marvell, TI or ADI. Every project is designed, verified with real simulators, signed off the way a product team would, and checked against broken copies of itself to prove the tests are not lying. Every project also answers four questions, which are what separate product work from coursework:

1. Will it fail in silicon? Corners, Monte Carlo, metastability, reliability, layout parasitics.
2. How do we know? Formal proofs, outside reference models, coverage, models checked against transistors.
3. What did it cost? Area, power, energy per operation, all measured.
4. What was the alternative? At least one design choice per project is built two ways and decided by numbers.

Everything is built in the open. Every design is visible at any time.

## The chip

```
supplies    3.3 V in -> bandgap_ldo -> 1.2 V analog; power_manager -> 0.9 to 1.2 V cpu supply (DVFS)
signal      sensor (0.2 to 1.0 V, up to 50 kHz)
              -> opamp        inverting amplifier, gain -1 around 0.6 V, drives the ADC
              -> adc          8-bit SAR ADC, 1 MS/s
              -> fifo_bridge  async FIFO + AXI4-Stream skid buffer, 10 MHz -> 50 MHz
              -> cpu          RV32I, machine mode, sets the DVFS state
flagships   tensor_core and coherent_noc (digital), serdes_frontend and lc_vco (analog),
            serdes_link and frac_n_pll (AMS: the PLL clocks the link, the VCO sits inside the PLL)
```

### Why the core numbers are what they are

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

Every target in this plan that is not forced by arithmetic is my own pick. If a real design cannot reach one, I relax it and write down why.

## Measured on this setup

Inside `iic-osic-tools:2026.10`, 21 Nov 2026:

- PDK: `/foss/pdks/ihp-sg13g2`. MOS models `cornerMOSlv.lib` and `cornerMOShv.lib` (PSP103 OSDI), SiGe HBTs (`cornerHBT.lib`, npn13G2), resistors, MIM and MOM caps, MOS varactors, ESD and bond-pad models. KLayout cells for inductors, HBTs and guard rings. Standard cells at slow (1.08 V, 125 C), typical (1.2 V, 25 C) and fast (1.32 V, -40 C). IHP SRAM macros (`RM_IHPSG13_1P_*`). Layer colours in `sg13g2.lyp`.
- Tools: ngspice 47, Xyce 7.10, Icarus 14.0-devel, Verilator 5.052, Yosys 0.70, SBY 0.70, eqy 0.70, OpenROAD 26Q4, OpenSTA 3.1.0, LibreLane 3.1.0.dev3, Magic 8.3.685, KLayout 0.30.12, Netgen 1.5.324, Xschem 3.4.8RC, cocotb 2.1.0, pyuvm 5.0.0, Fault 0.9.4, FuseSoC 2.4.7, opencdc 0.4.1, openEMS, Palace, OpenVAF, spicebind, CVC, padring, Verible, slang, scikit-rf 2.1.0, numpy 2.5.4, scipy 1.18.1, matplotlib 3.11.2, riscv64-unknown-elf-gcc 16.1.0, Spike, Node 18
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
10. Every behavioral model (real-number SystemVerilog or Verilog-A) is checked against the transistor circuit it stands for, with the allowed error written down, before any system result uses it.
11. Every analog layout is generated by a KLayout script from the PDK cells, so it can be rebuilt and reviewed like code.
12. Balance: `tracking/balance.py` reports hours and finished checks per track. No track may fall more than 10% behind the other two.

## Folders

```
README.md            what this is and how to run it
plan.md              this file
chip.md              whole-chip spec
Makefile             make check_tools | make tools | make all | make compare | make honesty | make console
setup/               start_tools.sh, run.sh, check_tools.sh, get_tools.sh
helpers/             save_result.py, check_honesty.py, cocotb_run.py, cpu_model.py, cdc_check.py, mtbf.py,
                     transistor_charts.py, opamp_sizing.py, analog_results.py, adc_spectrum.py,
                     number_formats.py, eye_diagram.py, phase_noise.py
projects/
  digital: fifo_bridge/ cpu/ tensor_core/ coherent_noc/
  analog:  opamp/ bandgap_ldo/ serdes_frontend/ lc_vco/
  ams:     adc/ power_manager/ serdes_link/ frac_n_pll/
  whole_chip/
compare_with_papers/ transistors/, ota_5t/, cummings_fifo/, reference_block/, report.md
console/             read-only viewer: schematics, layouts, waveforms, results, 3D die
hardware/            stm32_dac/, tang_nano/
tracking/            log_session.py, balance.py, scorecard.md
```

Every project folder looks the same, so it can be copied out as its own repo:

```
README.md     spec, block diagram, results table, design review, interview questions, things to try
design/       the design (RTL, schematics, layout scripts, behavioral models)
tests/        testbenches
formal/       formal checks (digital)
timing/       synthesis, timing, power, equivalence and test scripts (digital)
layout/       layout script, DRC, LVS, extraction
broken/       three small patches that break the design on purpose
results/      summary.json + raw logs
Makefile      make test | formal | timing | layout | broken | all, where each applies
```

Each README has a design review: what was tried, what failed, the numbers, and why the final choice won.

## Signoff checks

### Every digital block

| Check | Tool | Pass rule |
|---|---|---|
| Timing at three corners | Yosys mapping (with ABC buffering and sizing), OpenSTA on the slow, typical and fast libraries | no negative setup slack at slow, no negative hold slack at fast |
| Power | OpenSTA with switching activity from a VCD written by the cocotb run | number reported per corner, activity source named |
| Clock and reset crossings | `cdc_check.py` on the Yosys netlist, formal proof that each Gray pointer changes at most one bit per cycle, opencdc as a second opinion | every crossing lands on a two-flop chain with no logic in front, multi-bit crossings proved Gray, every reset released through a reset synchronizer; probe designs show what each checker catches and misses |
| RTL vs netlist | eqy | equivalent |
| Scan and test patterns | Fault | coverage reported, not hidden |
| Layout | LibreLane to GDS, KLayout DRC, Netgen LVS, OpenROAD timing and IR drop after routing | clean, or the failures listed |

### Every analog and AMS circuit

| Check | Tool | Pass rule |
|---|---|---|
| Corners | ngspice: TT/SS/FF/SF/FS x -40/27/125 C x supply +-10% | every spec met, worst corner named |
| Mismatch and process | ngspice Monte Carlo, 200 runs quick, 1000 full | yield per spec and combined |
| Noise | ngspice noise and transient noise | integrated over the band that matters |
| Reliability | CVC voltage checks (no thin-oxide device over 1.32 V), current density per wire against the PDK limits | clean, or listed |
| Layout | KLayout script, KLayout DRC, Netgen LVS, Magic extraction | clean, then every spec re-run on the extracted netlist and shown next to the schematic result |
| Model match | real-number or Verilog-A model against the transistor circuit | within the stated error, else the model is not used |

## Digital VLSI track

### fifo_bridge (core): a clock-crossing block you could ship
- Design: Gray-code async FIFO (16 deep, 8 data bits + last), two-flop synchronizers in their own module, skid buffer with a registered `tready`, top-level bridge.
- Reset crossing done right: one reset input, a reset synchronizer per clock (asserts at once, releases on its own clock), and `tready` held low until the write side is out of reset. The textbook version accepts a word in the first cycles after reset and loses it; a test shows that.
- Metastability injection: the synchronizer has a simulation mode where each bit that changed just before the clock edge randomly lands one cycle late, the way a real flop can resolve. Traffic must still lose nothing. The design review covers two findings from building it: a simpler injection model fails a correct FIFO by inventing values real hardware cannot produce, and a binary pointer survives injection in this FIFO because full and empty are equality tests and each side moves one word per cycle; it would break as soon as the pointer is used as a fill level.
- Synchronizer MTBF from transistor physics: ngspice sweeps data-to-clock timing on the real IHP flop netlist, `mtbf.py` fits the resolution time constant and window from the ngspice output, and the report gives MTBF for 2 and 3 flops at 10 and 50 MHz at each corner.
- Tests: cocotb random traffic in both clock directions, 80k+ words, zero loss, duplication or reordering, AXI stability while stalled, checks that the FIFO really filled and emptied.
- Formal: full proofs of the FIFO and the skid buffer, a 40-step bounded check of the joined bridge, the Gray one-bit proof, covers proving each rule is reached.
- Signoff: as above, plus a skew limit on the Gray bus in the timing constraints.
- Depth sizing: the README works out the minimum depth for a burst length and clock ratio; the tests show the measured limit matches.
- Broken copies: drop the word at the end of each memory lap, full check that inverts only the top Gray bit, output data that changes while stalled, and `full` reset low (the textbook reset value, which lets the bridge handshake while in reset).

### cpu (core): a core verified against the ISA
- Design: 5-stage RV32I with forwarding, load-use stall, branch flush, 2-bit predictor with a 16-entry BTB, performance counters, memory-mapped stream input.
- Machine mode: Zicsr, traps (illegal instruction, ecall, misaligned), timer and external interrupts, `wfi`. The filter firmware sleeps until a frame is ready; the power saving is measured.
- Formal ISA check: an RVFI port and riscv-formal, proving every instruction against the RISC-V spec, plus register, PC, causality and liveness checks.
- Random programs: riscv-dv's Python generator, run in lockstep against the reference model, which is checked against Spike.
- Compliance: rv32ui riscv-tests (passing now) and riscv-arch-test.
- Hardware and software together: one custom multiply-accumulate instruction for the FIR, with measured cycles per frame and area, with and without it.
- Measured trade-offs: CoreMark per MHz; BTB size (0, 4, 16, 64) and 2-bit vs gshare against mispredictions and area; forwarding on and off against CPI.
- Physical: LibreLane to GDS with IHP SRAM macros (1024 x 32) as instruction and data memory, full signoff, Fault scan and ATPG.
- On a board: CoreMark and the filter on the Tang Nano 20K, results over UART.
- Broken copies: no forwarding from MEM, missing load-use stall, no flush after a mispredict.

### tensor_core (flagship): mixed-precision AI arithmetic
- Design: 8x8 systolic array of fused multiply-add cells. Inputs BF16, FP8 E4M3 and E5M2, and OCP MX block formats (MXFP8 and MXFP4 with a shared E8M0 scale per 32 elements). FP32 accumulate, round to nearest even.
- Reference: FP8 and BF16 products are exact in FP32, so SoftFloat's `f32_mulAdd` on the widened inputs is a bit-exact reference for every cell. All 256 FP8 codes checked exhaustively in both formats. TestFloat runs the FP32 adder.
- Dataflow study: weight-stationary vs output-stationary, both built, measured utilization on a real convolution layer and a GEMM, and a roofline with the measured points on it.
- Performance model: a Python cycle model whose cycle counts match the RTL within 2% on every workload.
- Accuracy study: one real network layer in BF16, FP8 and MXFP4 against FP32, error reported.
- Physical: LibreLane to GDS, full signoff. A 4x4 version sized for a Tiny Tapeout IHP tile, prepared for the next IHP shuttle once its dates are announced; submitting costs money and is your call then.
- Broken copies: rounding toward zero, FP8 subnormals flushed to zero, block scale applied one element late.

### coherent_noc (flagship): coherence over a network, the way real many-core chips do it
- Design: 4 of our RV32I cores with private L1s on a 2x2 mesh. Routers with credit flow control, virtual channels and dimension-order routing. Directory-based MESI with the L2 split into slices built from IHP SRAM macros. Requests and responses on separate virtual channels so the protocol cannot deadlock the network. A die-to-die link (flits with CRC and a replay buffer) lets two halves of the mesh sit on separate dies.
- Verification: UVM testbench (Accellera UVM 2020.3.1 on Verilator, pyuvm if that does not hold up) with constrained random traffic, scoreboard and coverage closure reports. Formal proofs on a small configuration: at most one writer per line, every read sees the last write, no network deadlock, replay delivers every flit exactly once under injected bit errors. Memory-ordering litmus tests on the cores.
- Measured: L1 and L2 miss rates and average latency on CoreMark and Embench for 1, 2 and 4 cores; network latency vs injection rate under uniform, hotspot and transpose traffic.
- Physical: one tile (router, core, L1, L2 slice) to GDS with the SRAM macro placed, full signoff.
- Broken copies: a missed invalidate, credit returned one cycle early, replay that skips one flit.

## Analog VLSI track

### opamp (core): a sizing method you can trust, checked in its real load
- Design: two-stage Miller opamp with a nulling resistor. Layout with a common-centroid input pair, interdigitated mirrors and guard rings.
- Sizing method: ngspice sweeps the real IHP transistors into gm/Id tables; `opamp_sizing.py` picks every W and L from the tables and the spec by arithmetic alone; ngspice then checks the result. Predicted vs simulated values are reported, so the method itself is tested.
- In its real load: besides an ideal 2.05 pF cap, it drives the ADC's sampling switch and capacitor DAC with the comparator's kickback.
- Full spec set: gain, GBW, phase margin (Tian, in the real loop), slew, settling to half an LSB, output swing, input noise integrated over the ADC band against kT/C and the LSB, PSRR, CMRR, power.
- Yield: corners and 1000 Monte Carlo runs, yield per spec and combined.
- Design-review comparison: Miller with a nulling resistor against indirect (cascode) compensation, on settling, power and area.
- An ideal two-pole model runs through the same scripts, to prove the measurement scripts are right.
- Broken copies: phase margin under 20 deg, GBW/slew below spec, gain under 45 dB.

### bandgap_ldo (core): the chip's own supply and reference
- Design: bandgap reference on the 3.3 V supply using the process's PNP devices, with a start-up circuit and a trim network; capacitor-less LDO making 1.2 V from 3.3 V with a thick-oxide pass device, 0 to 20 mA.
- Specs (my picks): reference temperature coefficient under 30 ppm/C from -40 to 125 C after trim; LDO PSRR better than 40 dB at 1 kHz and 20 dB at 1 MHz; under 50 mV droop on a 0 to 20 mA step in 100 ns; stable across the whole load range with no external cap; quiescent current under 100 uA.
- Studies: trim yield from Monte Carlo (how many trim bits are really needed); start-up from every supply ramp rate; stability across load with the loop gain measured by Tian's method.
- Reliability: CVC confirms no thin-oxide device sees more than 1.32 V during start-up or any load step.
- Layout: common-centroid PNP array and resistor matching, extracted re-check.
- Broken copies: start-up circuit removed, trim applied with the wrong sign, LDO compensation that rings on a load step.

### serdes_frontend (flagship): high-speed analog with SiGe transistors
- Design: CML transmitter driver with a 3-tap feed-forward equalizer built on the process's npn13G2 HBTs, continuous-time linear equalizer with adjustable peaking, and a fast sampler. Bond pad and ESD from the PDK models at both ends.
- Target (my pick): 10 GBd, so 10 Gb/s NRZ and 20 Gb/s PAM4; 25 Gb/s NRZ as a stretch.
- Specs: output swing and rise time, return loss with pad and ESD, CTLE peaking range, sampler sensitivity and metastability window, power per Gb/s.
- Electromagnetics: the on-chip inductive peaking coil is simulated in openEMS, and its extracted model is used in the circuit.
- Layout: driver, CTLE and sampler, extracted; post-layout eye compared with the schematic eye.
- Broken copies: CTLE zero misplaced, FFE tap with the wrong sign, sampler with a 30 mV offset.

### lc_vco (flagship): RF oscillator design
- Design: 10 GHz LC VCO with a cross-coupled pair, MOS varactors and a switched capacitor bank for coarse tuning.
- Inductor: drawn with the PDK inductor cell, simulated in openEMS (and Palace as a cross-check) for L, Q and self-resonance, compared with the PDK's own inductor model.
- Specs (my picks): tuning range covering 9 to 11 GHz across corners; phase noise better than -100 dBc/Hz at 1 MHz offset; power under 10 mW.
- Phase noise: from ngspice transient noise, folded into jitter and then phase noise by `phase_noise.py`, and checked against Leeson's formula using the simulated tank Q.
- Studies: CMOS cross-coupled pair vs HBT pair on phase noise and power; tail filtering on and off.
- Layout with the inductor, extracted re-check of frequency and phase noise.
- Broken copies: tank Q halved, varactor polarity reversed, start-up gain under 1 at the slow corner.

## AMS track

### adc (core): an architecture choice backed by energy numbers
- Architecture study: conventional, monotonic and Vcm-based capacitor switching, compared on energy per conversion (from ngspice supply current), DAC area and linearity. The winner is chosen by those numbers.
- Timing: asynchronous (self-timed) SAR logic against a 10 MHz synchronous version, on power, the clock it needs and the metastability rate.
- Comparator: StrongARM latch; offset from Monte Carlo, noise from transient noise, kickback, decision time vs input.
- Full transistor-level FFT: coherent sine input, 128 points quick, 1024 full; ENOB, SNDR and SFDR at every corner; histogram DNL/INL; offset and gain error.
- Mixed-signal simulation: the SAR logic RTL runs against the transistor comparator and DAC in one simulation (spicebind or ngspice digital co-simulation).
- Where it stands: Walden and Schreier figures of merit, plotted on Murmann's published ADC survey (pinned revision) next to real published converters.
- Layout: common-centroid MIM capacitor array and comparator, post-layout ENOB.
- A real-number model fitted to the transistor results drives `whole_chip`.
- An ideal 8-bit quantizer, run in Verilator, must score ENOB 8.0 +- 0.1.
- Broken copies: +2 LSB comparator offset, 10% MSB cap mismatch, non-coherent test tone.

### power_manager (core): digital power control, the way large chips handle supply droop
- Design: digital LDO (comparator, PMOS switch array, digital controller) giving the cpu 0.9 to 1.2 V in four DVFS states set by a cpu register; a droop detector (a delay line that measures the supply) that stretches the cpu clock when the supply sags; power-on reset and brown-out detector.
- Mixed-signal: the controller RTL runs against the transistor switch array and comparator; a real-number model of the whole loop is checked against it.
- Measured: DVFS transition time; droop on a load step with and without clock stretching; limit-cycle ripple and how the controller design changes it; energy per filter frame at each DVFS state, run by the real firmware.
- Layout of the switch array and comparator, extracted.
- Broken copies: controller gain too high (limit cycle grows), clock stretch disabled, brown-out threshold off by 100 mV.

### serdes_link (flagship): the full link, from bits to bit error rate
- Design: the serdes_frontend circuits plus the digital and mixed-signal loops around them: 1-tap decision feedback equalizer with sign-sign LMS adaptation, bang-bang clock recovery with a digital loop filter and a phase interpolator, PRBS7/PRBS31 generator and checker.
- Channel: lossy transmission lines in ngspice sized for about 15 dB loss at Nyquist, and scikit-rf to check the channel's frequency response.
- Simulation: real-number models of each analog block, checked against the transistor circuits, run millions of bits; transistor co-simulation for the eye at key points.
- Measured: eye diagrams and bathtub curves for NRZ and PAM4, bit error count, jitter tolerance against a sinusoidal jitter mask, adaptation convergence time. `eye_diagram.py` only folds simulator output into eyes; PyBERT is an independent cross-check.
- Broken copies: LMS sign flipped, CDR loop gain too high, PAM4 thresholds swapped.

### frac_n_pll (flagship): a fractional-N synthesizer around the lc_vco
- Design: phase-frequency detector, charge pump, passive loop filter, the lc_vco, a programmable divider, and a third-order MASH sigma-delta modulator in RTL for fractional division. Makes the 10 GHz serdes clock from a 50 MHz reference.
- Loop design: a phase-domain model sets bandwidth and phase margin; the transistor loop is checked against it.
- Specs (my picks): lock under 20 us; integrated jitter under 2 ps rms (10 kHz to 100 MHz); fractional spurs reported.
- Measured: lock transient, phase noise of the loop (in-band from the charge pump and reference, out-of-band from the VCO), spurs, charge-pump mismatch effect.
- Layout of the charge pump, PFD and divider, extracted.
- Broken copies: charge-pump up/down mismatch of 20%, loop filter zero removed, sigma-delta order dropped to 1.

## whole_chip: integration across all three tracks
- Real-number models of the opamp, adc, bandgap_ldo and power_manager (each checked against its transistors) drive fifo_bridge and the cpu RTL in one mixed-signal simulation.
- Scenarios: power-on (bandgap start-up, LDO ramp, reset release), a sensor waveform through every block to filter results, DVFS changes ordered by firmware, a load step causing a droop and a clock stretch.
- Checks: frames arrive intact, no overflow, filter outputs match a Python reference, the cpu sleeps between frames, energy per frame reported.
- Top-level layout: blocks placed in a pad ring (padring tool), top-level DRC and LVS.

## Comparing with published work

`make compare` writes `compare_with_papers/report.md`, with our value, the published value, the exact source and the difference:

- IHP transistor threshold, current and gm/Id, against IHP's own `SG13G2_os_process_spec.pdf` (only numbers that are actually in it)
- JKU 5-transistor OTA from the IHP tutorial: simulation, DRC, LVS
- Cummings SNUG-2002 async FIFO: formal + cocotb on the original, fails when one line is broken
- The LibreLane reference block bundled with the PDK: cells, area, fmax
- Our ADC on Murmann's survey; each flagship against one published design in a similar process, numbers quoted only from the paper itself

Where no published number exists, the report says so.

## What the lab shows an employer

| What hiring teams ask for | Where it is shown |
|---|---|
| Microarchitecture and RTL | cpu, tensor_core, coherent_noc |
| SystemVerilog, UVM, coverage closure | coherent_noc |
| Formal verification | fifo_bridge, cpu (riscv-formal), coherent_noc |
| Clock and reset crossing signoff | fifo_bridge |
| Computer arithmetic, low-precision AI formats | tensor_core |
| Caches, coherence, interconnect, chiplet links | coherent_noc |
| Performance modeling correlated with RTL | tensor_core, cpu |
| Synthesis, timing, power, DFT, place and route | every digital block |
| Transistor-level analog design and layout | opamp, bandgap_ldo, serdes_frontend, lc_vco |
| Precision analog, references and regulators | bandgap_ldo |
| High-speed and RF design, electromagnetics | serdes_frontend, lc_vco |
| Data converters | adc |
| SerDes equalization and clock recovery, NRZ and PAM4 | serdes_link |
| Frequency synthesis, phase noise, jitter | frac_n_pll, lc_vco |
| Digital power management, droop response, DVFS | power_manager |
| Mixed-signal verification with models checked against transistors | adc, power_manager, serdes_link, whole_chip |
| Yield, corners, reliability | every analog and AMS block |

Where the industry is heading, and where it shows up here: low-precision and block-scaled AI number formats (tensor_core), chiplets and die-to-die links (coherent_noc), PAM4 links (serdes_link), digitally assisted analog such as digital LDOs and adaptive clocking for droop (power_manager), model-based mixed-signal verification (whole_chip), and analog layout written as code (every analog layout).

## Console

`make console` opens a read-only viewer in the style of a professional layout and schematic tool (Vite + React + three.js + uPlot). It never edits anything, and it uses no product names, logos, icons or dialogs from any vendor; every icon is drawn for this project.

- **Shell:**
  - Library tree on the left: the three tracks, one entry per block, with its views (schematic, layout, waveforms, results, 3D die).
  - Layer palette on the right, filled from the IHP SG13G2 KLayout `.lyp` file: real layer names, colours and stipple patterns, each with a visibility toggle.
  - Command log at the bottom: every file the viewer loaded, with its SHA-256 from `summary.json`.
  - Status bar: cursor X/Y in um, zoom, the open cell, and the result of the open block.
  - Black canvas with a dot grid.
- **Schematic view:** the xschem SVG export of each schematic, with pan and zoom.
- **Waveform view:** black background, coloured traces, two click cursors with delta readout. Data comes straight from the real ngspice `.raw` files, parsed in the browser.
- **Layout view:** the GDS exported by a KLayout script, drawn with the PDK's layer colours and stipples.
- **3D die view:** the die on its package, one tile per block coloured by result (grey not run, green pass, red fail). Signal particles flow only through passing blocks. Click a tile to open its layout.
- **Results view:** each check with its log and hash, the broken-copy table, the comparison table, and plots from the logs (Bode, step response, FFT, DNL/INL, gm/Id, eye, phase noise, IPC, timing slack).
- **Balance view:** hours and finished checks per track, from `tracking/balance.py`.
- **Open in xschem / KLayout:** buttons that show the exact shell command to open the same file in the real tool. The viewer does not run it.
- **Reliability:** it only shows data read from `results/`. A block with no `summary.json` shows as "not run". A reduced-motion switch turns off camera moves and particles.

## Hardware

- **stm32_dac:** 8-bit R-2R DAC on a breadboard, driven and measured by the Nucleo-H753. `adc_spectrum.py` computes DNL/INL/ENOB from the measured data, the same script the adc uses.
- **tang_nano:** fifo_bridge and cpu on a Tang Nano 20K (Gowin GW2AR-18), CoreMark and the filter results over UART. Open-source flow: Yosys + nextpnr-himbaechel + apicula + openFPGALoader.

## Tools

Tools already in `iic-osic-tools:2026.10` are used as the image ships them. Everything else is fetched by `make tools` (`setup/get_tools.sh`) into `third_party/` or `build/`, never committed, at the exact version below. `setup/check_tools.sh` checks every one and fails if any is missing.

| Need | Tool | Version |
|---|---|---|
| UVM | Accellera UVM-SV (`accellera-official/uvm-core`) | tag 2020.3.1 |
| Solvers | Bitwuzla | 0.8.2 |
| | Boolector | 3.2.4 |
| Equivalence | eqy | image (0.70) |
| Scan and test patterns | Fault | image (0.9.4) |
| Clock crossings | opencdc | image (0.4.1) |
| SRAM | IHP SRAM macros `RM_IHPSG13_1P_*` | image PDK |
| ISA formal | riscv-formal | c992aa61fdfe |
| Random programs | riscv-dv | f557b89ed688 |
| CPU tests | riscv-tests | 3df703cd52d5 |
| | riscv-arch-test | tag 3.10.0 |
| | CoreMark (`eembc/coremark`) | 1f483d5b8316 |
| | Embench IoT | 09c2ed8c3b70 |
| Number formats | Berkeley SoftFloat 3 | 07ebd29db0cf |
| | Berkeley TestFloat 3 | a9c849f1b0eb |
| Mixed-signal simulation | spicebind, ngspice digital co-simulation | image |
| Behavioral models | OpenVAF (Verilog-A) | image |
| Electromagnetics | openEMS, Palace | image |
| Reliability | CVC | image |
| Pad ring | padring | image |
| ADC comparison | Murmann ADC survey | 00b4b855de5c (rev20260801) |
| SerDes | scikit-rf | image (2.1.0) |
| | PyBERT, as a cross-check of `eye_diagram.py` | tag v11.2.0 |
| Python | numpy, scipy (FFT and filters only), matplotlib | image |
| Packaging | FuseSoC | image (2.4.7) |
| Tiny Tapeout | tt-support-tools | 0922544e6c7f |
| Tang Nano 20K | nextpnr (himbaechel, Gowin) | tag nextpnr-0.11.1 |
| | apicula | 0.35 |
| | openFPGALoader | tag v1.2.0 |
| STM32 | arm-none-eabi-gcc (Arm GNU Toolchain) | 14.3.rel1 |
| | libopencm3 | a3977e14519e |
| | OpenOCD | tag v0.12.0 |
| Console | Node LTS | 24.11.1 |
| | Vite, React, three.js, uPlot | pinned in `console/package-lock.json` |

## Using it

Each project README ends with "things to try": three changes to make yourself. Log each session with `tracking/log_session.py`, which records the track. `tracking/balance.py` shows the split, and the build order below keeps the three tracks moving together.

## Build order

Work goes in rounds. Each round finishes one project in every track, so the split stays at a third each. A project is finished when all of its files pass, its three broken copies are caught, its signoff checks are logged, the honesty check passes, and it is committed.

0. Done: setup, helpers, honesty check, tracking, `chip.md`; cpu tests, timing and broken copies.
1. `make tools`: fetch and check every pinned extra; replace `decide.py` with `balance.py`.
2. Round 1: fifo_bridge (digital), transistor charts and opamp (analog), adc (AMS).
3. Round 2: cpu upgrades and layout (digital), bandgap_ldo (analog), power_manager (AMS).
4. Round 3: whole_chip, console, compare_with_papers.
5. Round 4: tensor_core (digital), serdes_frontend (analog), serdes_link (AMS).
6. Round 5: coherent_noc (digital), lc_vco (analog), frac_n_pll (AMS).
7. Hardware, Tiny Tapeout preparation, and a fresh-clone check that every result reproduces.

## Risks

- VCS, Xcelium and Spectre targets cannot be tested here.
- Some published numbers may not exist in the IHP documents. The report will say so.
- Verilator runs most but not all of UVM; pyuvm is the fallback.
- 8x8 may not fit a Tiny Tapeout tile; 4x4 is the fallback.
- Open tools have no UPF power-intent flow, so the multi-voltage checks are done by simulation, and that limit is stated.
- ngspice has no periodic steady-state or periodic noise analysis, so phase noise comes from transient noise and is checked against Leeson's formula; that is slower and less exact than a commercial simulator, and the report says so.
- The full bridge proof did not finish in 20 minutes; it is split into full proofs of each half plus a bounded check of the whole.
- Scripted analog layout is the hardest part. If a layout cannot be made DRC/LVS clean, it gets reported, not hidden.
- SerDes, PLL and full-ADC transistor simulations are slow; each has a quick mode and a full mode.
- High-speed targets (10 GBd, 10 GHz) rest on the HBT and inductor models; if extraction shows they are out of reach, the target is lowered and the reason written down.
- This cloud machine is wiped between sessions. Everything is committed as it goes, and `setup/start_tools.sh` plus `make tools` rebuild the tools.
