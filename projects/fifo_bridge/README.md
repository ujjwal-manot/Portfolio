# fifo_bridge

Carries the ADC's 8-bit samples, with a frame-end flag, from the 10 MHz ADC clock to the 50 MHz CPU clock. The two clocks are unrelated, so every word has to cross safely: none lost, none doubled, none out of order.

## Spec

| Item | Value |
|---|---|
| Input | AXI4-Stream on `s_clk` (10 MHz): `s_tvalid`, `s_tready`, `s_tdata[7:0]`, `s_tlast` |
| Output | AXI4-Stream on `m_clk` (50 MHz): `m_tvalid`, `m_tready`, `m_tdata[7:0]`, `m_tlast` |
| Depth | 16 words of 9 bits (data plus `tlast`), plus 2 in the output stage |
| Throughput | one word per clock on both sides |
| Reset | one `rst_n`, active low; `reset_sync` gives each clock its own copy that asserts at once and releases on that clock |
| Timing | IHP slow, typical and fast corners, no negative slack, before and after layout |

## How it works

```
 s_clk side                                 |            m_clk side
                                            |
 s_tdata,s_tlast --> [ 16 x 9 memory ] -----+----> r_data --> [ skid_buffer ] --> m_tdata,m_tlast
 s_tvalid ---------> w_bin, w_gray  --------+--> sync2 --> compare --> r_ready (= not empty)
 s_tready <-- w_room <-- compare <-- sync2 <--+-- r_gray, r_bin <-- take <-- skid s_ready
```

- `design/async_fifo.sv`: the pointers count in binary and are sent across as Gray code, where only one bit changes per step, so a synchronizer that catches a changing pointer sees either the old or the new value, never a mix. Full and empty are worked out on each side from its own pointer and the other side's pointer after `sync2`. Both are pessimistic: the writer may think the FIFO is fuller than it is and the reader may think it is emptier, never the dangerous way round. IHP has only reset-to-0 flops, so the design stores "room" and "ready" (full and empty inverted); otherwise synthesis would invert those flops and the cell netlist would no longer match the RTL register for register.
- `design/sync2.sv`: two flops per bit. With `METASTABLE` defined (Icarus), a bit that changed inside the spread of the flop's measured flip point lands old or new at random. Under `FORMAL`, any bit that changed since the last edge may land old or new, as the solver chooses, and a cover shows a changed bit really landing old.
- `design/reset_sync.sv`: one per clock, so reset asserts at once and releases in step with that clock.
- `design/skid_buffer.sv`: a two-register output stage. Its `s_ready` comes straight from a flop, so a slow `m_tready` never reaches back into the FIFO in the same cycle, and it still moves one word per clock.
- `design/fifo_bridge.sv`: joins them.

One netlist runs through everything after synthesis: `timing/synth.ys` maps the RTL to IHP cells, and that same netlist is what eqy proves equal to the RTL, what the cell-level CDC check reads, what the timed gate runs simulate, and what LibreLane places and routes (it only elaborates it). The routed netlist is that netlist plus clock trees, buffers and split tie cells; LVS ties it to the layout, `formal/routed.eqy` proves it equal to the mapped netlist, and it gets its own CDC check, timing and timed simulation.

## Metastability, measured

`make mtbf` extracts the IHP `sg13g2_dfrbpq_1` flop from its own layout with Magic (every resistor and capacitor), drives and loads it with real IHP cells in ngspice, finds the exact data time where capture flips by 50 bisection steps, then moves the data edge toward that point from both sides and records when Q last leaves a 10% band around its final level. It does this at tt (1.2 V, 27 C), ss (1.08 V, 125 C) and ff (1.32 V, -40 C), for rising and falling data.

`mtbf/mtbf.py` fits settle time = a - tau ln(gap) only over the stretch where each step follows the log law within 15%, stops where the solver no longer resolves the gap, and works out MTBF for both pointer crossings using the time left in each destination clock period after the liberty setup time. The spread of the flip point over the six runs is the window `sync2.sv` uses for its random injection, and `mtbf.py` fails if the two ever disagree.

| Corner, data edge | tau | Flip point before CLK | Liberty setup | Bridge MTBF | Where |
|---|---|---|---|---|---|
| tt, rise | tau 71.1 ps | flip 104.6 ps | liberty setup 112.5 ps | bridge MTBF 10^109 years | `results/mtbf.log` |
| tt, fall | tau 66.8 ps | flip 100.5 ps | liberty setup 112.5 ps | bridge MTBF 10^116 years | `results/mtbf.log` |
| ss, rise | tau 133.8 ps | flip 177.0 ps | liberty setup 190.7 ps | bridge MTBF 10^51 years | `results/mtbf.log` |
| ss, fall | tau 125.6 ps | flip 160.6 ps | liberty setup 190.7 ps | bridge MTBF 10^55 years | `results/mtbf.log` |
| ff, rise | tau 37.5 ps | flip 70.4 ps | liberty setup 75.8 ps | bridge MTBF 10^218 years | `results/mtbf.log` |
| ff, fall | tau 36.5 ps | flip 61.6 ps | liberty setup 75.8 ps | bridge MTBF 10^224 years | `results/mtbf.log` |

The MTBF is huge because both clocks are slow next to tau: even the 50 MHz side leaves almost 20 ns, about 150 tau at the slow corner, for a metastable flop to settle. The flip point always sits inside the liberty setup time, as it should.

## Results

All numbers come from `results/`; every log there is hashed in `results/summary.json` together with the sources and helpers that made it.

The random tests take a new seed every run (printed at the top of each log, and replayable with `RANDOM_SEED=<seed>`), so counts such as the injected delays differ a little from run to run.

| Check | Result | Where |
|---|---|---|
| async_fifo, random phase and 100 to 1000 ppm offset, with and without metastability injection; never over 16 words, runs empty | pass, metastability injection delayed 75, 125 and 250 pointer bits | `results/test_async_fifo.log` |
| skid_buffer: random stalls, full rate, registered `s_ready` | pass | `results/test_skid_buffer.log` |
| fifo_bridge: frames both clock directions, resets mid-traffic (every other one with the bridge full), ADC feed, CPU pause | pass, metastability injection delayed 32, 51 and 90 pointer bits | `results/test_fifo_bridge.log` |
| Longest CPU pause with the ADC at 1 MS/s (18-word capacity), both runs | 18 us with 0 samples lost; samples lost from 19 us | `results/test_fifo_bridge.log` |
| Formal proof, async_fifo (4 deep), synchronizers may land old or new: no overflow, full and empty never wrong, every word intact, Gray pointers move one bit | proved | `results/formal_fifo_proof.log` |
| Formal proof, skid_buffer | proved | `results/formal_skid_proof.log` |
| Bounded check of the joined bridge | pass | `results/formal_bridge_check.log` |
| Covers: every rule reached, and both synchronizers seen landing a changed bit old | reached | `results/formal_fifo_reach.log` |
| Clock crossings, RTL: every crossing on a two-flop chain, multi-bit crossings Gray, resets synchronized | 0 unwaived crossing problems, 4 waivers | `results/cdc.log` |
| Clock crossings, cell netlist, same rules and waivers | 0 unwaived crossing problems, 4 waivers | `results/cdc_cells.log` |
| Clock crossings, routed netlist (clock trees and buffers in place), same rules and waivers | 0 unwaived crossing problems, 4 waivers | `results/cdc_routed.log` |
| Cells, mapped at the slow corner | chip area 16708.8 um2, 1015 cells, 208 sg13g2_dfrbpq_1 flops | `results/synth.log` |
| Cell netlist equals RTL (eqy) | Successfully proved designs equivalent | `results/equiv.log` |
| Routed netlist equals the mapped netlist (eqy; a one-gate change in a copy fails it) | Successfully proved designs equivalent | `results/equiv_routed.log` |
| Before layout: setup slack at slow, hold slack at fast | worst setup slack 14.9592 ns at slow; worst hold slack 0.1232 ns at fast | `results/timing_slow.log`, `results/timing_fast.log` |
| Before layout: Gray pointer skew, worst | skew 0.0591 ns, margin 19.9409 ns to one m_clk period | `results/timing_slow.log` |
| Layout (LibreLane): DRC, LVS, antenna, slew, capacitance and fanout | layout clean: no DRC, LVS, antenna or electrical violation | `results/layout.log` |
| Layout size | design__die__area 50654.5 um2, design__core__area 41640.5 um2, design__instance__count__stdcell 1369 | `results/layout.log` |
| After layout (extracted wires, real clock trees): setup slack at slow, hold slack at fast | worst setup slack 14.6224 ns at slow; worst hold slack 0.1208 ns at fast | `results/timing_routed_slow.log`, `results/timing_routed_fast.log` |
| After layout: Gray pointer skew, worst | skew 0.0800 ns, margin 19.9200 ns to one m_clk period | `results/timing_routed_slow.log` |
| Icarus with conditional SDF arcs, one xor2 cell | merged: X rise after 0.1505 ns; as written: X rise after 0.1202 ns | `results/test_sim_sdf.log` |
| Timed gate runs (ADC test plus a clock-to-output check against STA), mapped and routed, three corners | 6 passed | `results/test_gates.log` |
| Clock to output, routed, slow, m_tvalid | routed slow m_tvalid rise: measured 0.7010 ns, STA 0.7018 ns | `results/test_gates.log` |
| Power from the timed run, mapped netlist, slow | Total 1.89e-04 W | `results/power_mapped_slow.log` |
| Power from the timed run, mapped netlist, typ | Total 2.26e-04 W | `results/power_mapped_typ.log` |
| Power from the timed run, mapped netlist, fast | Total 2.75e-04 W | `results/power_mapped_fast.log` |
| Power from the timed run, routed netlist with clock trees and wires, slow | Total 3.12e-04 W | `results/power_routed_slow.log` |
| Power from the timed run, routed netlist with clock trees and wires, typ | Total 3.86e-04 W | `results/power_routed_typ.log` |
| Power from the timed run, routed netlist with clock trees and wires, fast | Total 4.83e-04 W | `results/power_routed_fast.log` |
| Metastability (above) | worst bridge MTBF 10^51 years | `results/mtbf.log` |

### Broken copies

`make broken` applies each patch in `broken/` to a copy and runs every simulation test and the two formal tasks that cover the FIFO (`fifo_proof`, `fifo_reach`); a patch counts as caught only if something fails with the message its first line names.

| Patch | What it breaks | Caught by | Where |
|---|---|---|---|
| `drop_word_on_wrap` | loses the word at the end of each memory lap | AssertionError: word 15: got 0x0 | `results/drop_word_on_wrap.log` |
| `wrong_full_check` | full check inverts only the top Gray bit | AssertionError: wrote past full: 17 words held in a 16-word FIFO | `results/wrong_full_check.log` |
| `data_changes_while_stalled` | output data moves while `m_tready` is low | changed while m_tready was low | `results/data_changes_while_stalled.log` |
| `full_low_in_reset` | the FIFO takes words while in reset | AssertionError: bridge handshakes right after reset asserts | `results/full_low_in_reset.log` |
| `skid_word_survives_reset` | the skid register keeps a word through reset | AssertionError: after reset got 65 words | `results/skid_word_survives_reset.log` |
| `binary_pointers_cross` | pointers cross in binary instead of Gray | Assert failed in fifo_rules.dut: async_fifo.sv (the one-bit Gray rule); the simulation also wrote past full: 17 words held in a 16-word FIFO | `results/binary_pointers_cross.log` |
| `synchronizer_never_lands_old` | the formal synchronizer always lands the new value | Unreached cover statement at fifo_rules.dut.w_to_r: sync2.sv | `results/synchronizer_never_lands_old.log` |

## Design review

- **Depth.** The plan said 16 words lets the CPU pause 16 us. With the 2 output registers the capacity is 18 words, and the measured limit is 18 us: the ADC offers a sample every 1 us, and the samples already in flight cover the last one.
- **Room and ready instead of full and empty.** IHP has no set flops. Stored as full/empty, the reset value 1 made synthesis invert those flops, and `eqy` could no longer match them to the RTL register for register.
- **Metastability window.** The first version used the liberty setup and hold numbers as the window. Those are the cell vendor's margins, not where the flop actually flips; the SPICE sweep shows the flip point sits 8 to 30 ps inside setup, so the window now comes from that sweep.
- **Reset test.** One broken copy (`skid_word_survives_reset`) once passed every test: the test drains faster than it fills, so a reset landed with a word in the skid register only by chance. Half the resets now wait until the bridge is full.
- **Clock tree.** The first layout's s_clk root buffer drove 16 branches against the liberty fanout limit of 8: OpenROAD's H-tree split five levels deep but put buffers on only three. Larger sink clusters changed nothing; a buffer at least every 50 um of clock wire (`CTS_DISTANCE_BETWEEN_BUFFERS`) fixed it.
- **One netlist.** The first layout let LibreLane synthesize the RTL itself, which gave a different netlist (muxes instead of NAND trees) from the one eqy and the CDC check had cleared. LibreLane now takes the `synth.ys` netlist as it is.
- **SDF in Icarus.** OpenSTA writes conditional delay arcs that Icarus ignores, so it fell back to the plain arc: 0.1202 ns instead of 0.1505 ns for one xor2 edge. `timing/sim_sdf.py` gives each pin pair its slowest arc and folds the port wire delays (which Icarus cannot place) into the cell pins they touch; the gate runs then match STA at every output to 0.5 ps before layout and 2 ps after (the routed SDF has 1 ps steps).

## Not covered yet

- The wires are extracted with IHP's nominal rules only: the PDK ships no minimum or maximum RC rule files, so "three corners" means three cell libraries with nominal wires.
- LibreLane's own power and IR drop figures (in `results/layout.log`) are vectorless, from its default switching activity; the power above comes from the simulated traffic instead. IR drop from real switching is not run.
- No clock jitter: both clocks come from board oscillators (`chip.md`), so it is never measured here.
- The interface budget (20% of each clock period for the neighbouring block) is a design choice, not a measurement.
- Icarus skips the cell models' setup and hold checks in the timed gate runs; STA covers them.
- `eqy` merges flops with identical inputs on both sides first (`opt_merge -share_all`), treats the asynchronous resets as synchronous (`async2sync`), and proves each side's pointer registers as one partition, because synthesis shares the top bit of the binary and Gray pointers, which only match from reset. A one-gate change in the read logic still fails it. A difference that shows only while reset is asserted would not be seen by `eqy`; the reset tests and broken copies cover that.
- The proofs use a 4-deep copy (`DEPTH_LOG2 = 2`) so the solver finishes; the logic does not change with depth, only the pointer width. The joined bridge is a bounded check, not a full proof.

## Run it

```
make test      # cocotb simulations, plain and with metastability injection
make formal    # SymbiYosys proofs and covers, with synchronizers that may land old or new
make cdc       # clock crossing check on the RTL and on the cell netlist
make timing    # Yosys mapping to IHP cells, then OpenSTA at three corners and the SDF for Icarus
make layout    # LibreLane place and route, signoff checks, routed CDC check, routed STA
make equiv     # eqy: cell netlist against RTL
make power     # SDF timing check in Icarus, timed gate runs, OpenSTA power, mapped and routed
make mtbf      # flop extraction, ngspice sweeps, tau and MTBF
make broken    # each patch in broken/ must make the tests or proofs fail for its named reason
make all
```

## Interview questions

1. Why send Gray code across the clock boundary instead of binary?
2. Why does the full check invert the top two bits of the synchronized read pointer, not just the top one?
3. Why is it safe that full and empty are late? What would go wrong if they were early?
4. The MTBF here comes from a SPICE sweep of the real flop. Which number moves it the most, and why does the slow corner set the worst case?
5. Why does the depth have to be a power of two for this design? How would you build a 12-deep one?
6. Every crossing path is held under one m_clk period. Why that bound, and why is the Gray pointer skew reported on its own?
7. Why does the skid buffer need two registers to keep full throughput with a registered `s_ready`?
8. What does AXI4-Stream require of `tvalid` and `tdata` while `tready` is low, and how does the test check it?
9. Reset asserts at once but releases on each clock separately. What could go wrong if it released on both clocks at the same instant?
10. The formal proof lets every changing synchronizer bit land old or new. Why does that stand for metastability, and what does it not cover?

## Things to try

- Change `DEPTH_LOG2` to 3, rerun `make test timing`, and watch the area and the longest CPU pause the test finds.
- Look at `broken/binary_pointers_cross.patch`. Formal stops it at the Gray one-bit assertion, which only restates the encoding, but the simulation also loses data: the full check inverts the top two pointer bits, which is right for Gray code and wrong for binary. Change the full check to suit binary pointers and see whether anything still catches the copy, then work out why a multi-bit binary pointer crossing is unsafe even when every test passes.
- Halve the `m_clk` period in `timing/timing.tcl` and in `mtbf/mtbf.py`, and see what happens to slack and to MTBF.
