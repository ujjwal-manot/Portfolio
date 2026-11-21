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
| Timing | IHP slow, typical and fast corners, no negative slack |

## How it works

```
 s_clk side                                 |            m_clk side
                                            |
 s_tdata,s_tlast --> [ 16 x 9 memory ] -----+----> r_data --> [ skid_buffer ] --> m_tdata,m_tlast
 s_tvalid ---------> w_bin, w_gray  --------+--> sync2 --> compare --> r_ready (= not empty)
 s_tready <-- w_room <-- compare <-- sync2 <--+-- r_gray, r_bin <-- take <-- skid s_ready
```

- `design/async_fifo.sv`: the pointers count in binary and are sent across as Gray code, where only one bit changes per step, so a synchronizer that catches a changing pointer sees either the old or the new value, never a mix. Full and empty are worked out on each side from its own pointer and the other side's pointer after `sync2`. Both are pessimistic: the writer may think the FIFO is fuller than it is and the reader may think it is emptier, never the dangerous way round. IHP has only reset-to-0 flops, so the design stores "room" and "ready" (full and empty inverted); otherwise synthesis would invert those flops and the cell netlist would no longer match the RTL register for register.
- `design/sync2.sv`: two flops per bit. With `METASTABLE` defined (Icarus), a bit that changed inside the flop's measured capture window lands old or new at random. Under `FORMAL`, any bit that changed since the last edge may land old or new, as the solver chooses.
- `design/reset_sync.sv`: one per clock, so reset asserts at once and releases in step with that clock.
- `design/skid_buffer.sv`: a two-register output stage. Its `s_ready` comes straight from a flop, so a slow `m_tready` never reaches back into the FIFO in the same cycle, and it still moves one word per clock.
- `design/fifo_bridge.sv`: joins them.

## Metastability, measured

`make mtbf` extracts the IHP `sg13g2_dfrbpq_1` flop from its own layout with Magic (every resistor and capacitor), drives and loads it with real IHP cells in ngspice, finds the exact data time where capture flips by 50 bisection steps, then moves the data edge toward that point from both sides and records when Q last leaves a 10% band around its final level. It does this at tt (1.2 V, 27 C), ss (1.08 V, 125 C) and ff (1.32 V, -40 C), for rising and falling data.

`mtbf/mtbf.py` fits settle time = a - tau ln(gap) only over the stretch where each step follows the log law within 15%, stops where the solver no longer resolves the gap, and works out MTBF for both pointer crossings using the time left in each destination clock period after the liberty setup time. The spread of the measured flip point (61.6 to 177.1 ps before the clock) is the window `sync2.sv` uses for its random injection, and `mtbf.py` fails if the two ever disagree.

| Corner, data edge | tau | Flip point before CLK | Liberty setup | Bridge MTBF |
|---|---|---|---|---|
| tt, rise | 71.1 ps | 104.6 ps | 112.5 ps | 10^109 years |
| tt, fall | 66.8 ps | 100.5 ps | 112.5 ps | 10^116 years |
| ss, rise | 133.8 ps | 177.0 ps | 190.7 ps | 10^51 years |
| ss, fall | 125.6 ps | 160.6 ps | 190.7 ps | 10^55 years |
| ff, rise | 37.5 ps | 70.4 ps | 75.8 ps | 10^218 years |
| ff, fall | 36.5 ps | 61.6 ps | 75.8 ps | 10^224 years |

The MTBF is huge because both clocks are slow next to tau: even the 50 MHz side leaves almost 20 ns, about 150 tau at the slow corner, for a metastable flop to settle. The flip point always sits inside the liberty setup time, as it should.

## Results

All numbers come from `results/`; every log there is hashed in `results/summary.json` together with the sources and helpers that made it.

| Check | Result | Where |
|---|---|---|
| async_fifo, random phase and 100 to 1000 ppm offset, with and without metastability injection; never over 16 words, runs empty | pass, injection delayed 72, 127 and 251 pointer bits | `results/test_async_fifo.log` |
| skid_buffer: random stalls, full rate, registered `s_ready` | pass | `results/test_skid_buffer.log` |
| fifo_bridge: frames both clock directions, resets mid-traffic (every other one with the bridge full), ADC feed, CPU pause | pass, injection delayed 32, 58 and 92 pointer bits | `results/test_fifo_bridge.log` |
| Longest CPU pause with no lost sample (ADC at 1 MS/s, 18-word capacity) | 17 us; first loss at 18 us in one run, 19 us in the other | `results/test_fifo_bridge.log` |
| Formal proof, async_fifo (4 deep), synchronizers may land old or new: no overflow, full and empty never wrong, every word intact, Gray pointers move one bit | proved | `results/formal_fifo_proof.log` |
| Formal proof, skid_buffer | proved | `results/formal_skid_proof.log` |
| Bounded check of the joined bridge | pass | `results/formal_bridge_check.log` |
| Covers: every rule reached, and both synchronizers seen landing a changed bit old | reached | `results/formal_fifo_reach.log` |
| Clock crossings, RTL: every crossing on a two-flop chain, multi-bit crossings Gray, resets synchronized | 0 unwaived problems, 3 waivers | `results/cdc.log` |
| Clock crossings, cell netlist, same rules and waivers | 0 unwaived problems, 3 waivers | `results/cdc_cells.log` |
| Cells, mapped at the slow corner | 16708.8 um2, 1015 cells, 208 flops | `results/synth.log` |
| Setup slack at slow, hold slack at fast | 14.959 ns, 0.123 ns | `results/timing_slow.log`, `results/timing_fast.log` |
| Gray pointer skew, worst corner, against one m_clk period | 0.0574 ns | `results/timing_slow.log` |
| Cell netlist equals RTL (eqy) | every partition proved | `results/equiv.log` |
| Timed gate-level run (SDF delays) of the ADC test at slow, typical and fast | 3 passed | `results/test_gates.log` |
| Power from that run, slow / typical / fast (no clock tree yet) | 1.89e-04, 2.25e-04, 2.74e-04 W | `results/power_*.log` |
| Metastability (above) | worst bridge MTBF 10^51 years | `results/mtbf.log` |

### Broken copies

`make broken` applies each patch in `broken/` to a copy and runs every test; a patch counts as caught only if the tests fail with the message its first line names.

| Patch | What it breaks | Caught by |
|---|---|---|
| `drop_word_on_wrap` | loses the word at the end of each memory lap | `word 15: got 0x0` |
| `wrong_full_check` | full check inverts only the top Gray bit | `wrote past full: 17 words held in a 16-word FIFO` |
| `data_changes_while_stalled` | output data moves while `m_tready` is low | `changed while m_tready was low` |
| `full_low_in_reset` | the FIFO takes words while in reset | `bridge handshakes while in reset` |
| `skid_word_survives_reset` | the skid register keeps a word through reset | `after reset got 65 words` |

## Design review

- **Depth.** The plan said 16 words lets the CPU pause 16 us. With the 2 output registers the capacity is 18 words, and the measured limit is 17 us: the ADC offers a sample every 1 us, and the last one lands as the pause ends.
- **Room and ready instead of full and empty.** IHP has no set flops. Stored as full/empty, the reset value 1 made synthesis invert those flops, and `eqy` could no longer match them to the RTL register for register.
- **Metastability window.** The first version used the liberty setup and hold numbers as the window. Those are the cell vendor's margins, not where the flop actually flips; the SPICE sweep shows the flip point sits 8 to 30 ps inside setup, so the window now comes from that sweep.
- **Reset test.** One broken copy (`skid_word_survives_reset`) once passed every test: the test drains faster than it fills, so a reset landed with a word in the skid register only by chance. Half the resets now wait until the bridge is full.

## Not covered yet

- No layout, so no clock tree and no extracted wires. Timing and power use cell delays and pin loads only; the clock tree is missing from the power figures.
- No clock jitter: there is no measured source for it until `frac_n_pll` exists, and no number is made up in the meantime.
- The interface budget (20% of each clock period for the neighbouring block) is a design choice, not a measurement.
- Icarus skips the cell models' setup and hold checks in the timed gate run; STA covers them. The run also leaves out the input driver delay on the port wires, because Icarus cannot place a delay on a port; STA still counts it.
- `eqy` merges flops with identical inputs on both sides first (`opt_merge -share_all`), treats the asynchronous resets as synchronous (`async2sync`), and proves each side's pointer registers as one partition, because synthesis shares the top bit of the binary and Gray pointers, which only match from reset. A one-gate change in the read logic still fails it. A difference that shows only while reset is asserted would not be seen by `eqy`; the reset tests and broken copies cover that.
- The proofs use a 4-deep copy (`DEPTH_LOG2 = 2`) so the solver finishes; the logic does not change with depth, only the pointer width. The joined bridge is a bounded check, not a full proof.

## Run it

```
make test      # cocotb simulations, plain and with metastability injection
make formal    # SymbiYosys proofs and covers, with synchronizers that may land old or new
make cdc       # clock crossing check on the RTL and on the cell netlist
make timing    # Yosys mapping to IHP cells, then OpenSTA at three corners
make equiv     # eqy: cell netlist against RTL
make power     # SDF-timed gate-level run at three corners, then OpenSTA power
make mtbf      # flop extraction, ngspice sweeps, tau and MTBF
make broken    # each patch in broken/ must make the tests fail for its named reason
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
- Send the binary pointers across instead of the Gray ones, keep the full and empty checks as equality tests, and run `make formal`. Before it finishes, work out on paper whether it should fail, and why.
- Halve the `m_clk` period in `timing/timing.tcl` and in `mtbf/mtbf.py`, and see what happens to slack and to MTBF.
