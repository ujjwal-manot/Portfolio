# fifo_bridge

Carries the ADC's 8-bit samples, with a frame-end flag, from the 10 MHz ADC clock to the 50 MHz CPU clock. The two clocks are unrelated, so every word has to cross safely: none lost, none doubled, none out of order.

## Spec

| Item | Value |
|---|---|
| Input | AXI4-Stream on `s_clk` (10 MHz): `s_tvalid`, `s_tready`, `s_tdata[7:0]`, `s_tlast` |
| Output | AXI4-Stream on `m_clk` (50 MHz): `m_tvalid`, `m_tready`, `m_tdata[7:0]`, `m_tlast` |
| Depth | 16 words of 9 bits (data plus `tlast`), plus 2 in the output stage |
| Throughput | one word per clock on both sides |
| Resets | `s_rst_n`, `m_rst_n`, active low, one per clock |
| Timing | slow corner (1.08 V, 125 C), no negative slack |

## How it works

```
 s_clk side                                 |            m_clk side
                                            |
 s_tdata,s_tlast --> [ 16 x 9 memory ] -----+----> r_data --> [ skid_buffer ] --> m_tdata,m_tlast
 s_tvalid ---------> w_bin, w_gray  --------+--> 2 flops --> compare --> r_empty
 s_tready <-- w_full <-- compare <-- 2 flops <--+-- r_gray, r_bin <-- take <-- skid s_ready
```

- `design/async_fifo.sv`: the pointers count in binary and are sent across as Gray code, where only one bit changes per step. A synchronizer that catches a changing pointer therefore sees either the old or the new value, never a mix. Full and empty are worked out on each side from its own pointer and the other side's pointer after two flops. Both are pessimistic: the writer may think the FIFO is fuller than it is, and the reader may think it is emptier, but neither is ever wrong in the dangerous direction.
- `design/skid_buffer.sv`: a two-register output stage. Its `s_ready` comes straight from a flop, so a slow `m_tready` never reaches back into the FIFO in the same cycle, and it still moves one word per clock.
- `design/fifo_bridge.sv`: joins the two.

## Results

All numbers come from `results/`; every log there is hashed in `results/summary.json`.

| Check | Result | Where |
|---|---|---|
| async_fifo: 80000 random words, 3 clock ratios | pass | `results/test_async_fifo.log` |
| skid_buffer: 20000 words with random stalls, full rate, registered `s_ready` | pass | `results/test_skid_buffer.log` |
| fifo_bridge: 400 frames of 64 samples, both clock directions, outputs hold while stalled | pass | `results/test_fifo_bridge.log` |
| Formal proof, async_fifo (4 deep): never over 4 words, full and empty never wrong, every word arrives intact | FORMAL_FIFO | `results/formal_fifo_proof.log` |
| Formal proof, fifo_bridge (4 deep): never over 6 words, `tlast` and data intact, outputs hold while stalled | FORMAL_BRIDGE | `results/formal_bridge_proof.log` |
| Formal cover: each rule above is actually reached | pass | `results/formal_*_reach.log` |
| Cells, IHP slow corner | 15613 um2, 204 flops | `results/synth.log` |
| Timing, m_clk 50 MHz, s_clk 10 MHz | setup slack 15.0 ns, hold slack 0.29 ns | `results/timing.log` |
| Broken copy: drops the word at the end of each memory lap | caught | `results/drop_word_on_wrap.log` |
| Broken copy: full check inverts only the top Gray bit | caught | `results/wrong_full_check.log` |
| Broken copy: output data changes while `m_tready` is low | caught | `results/data_changes_while_stalled.log` |

The proofs use a 4-deep copy (`DEPTH_LOG2 = 2`) so the solver finishes. The logic does not change with depth; only the pointer width does.

## Run it

```
make test      # cocotb simulations (SIM=icarus also works)
make formal    # SymbiYosys proofs and covers
make timing    # Yosys mapping to IHP cells, then OpenSTA
make broken    # applies each patch in broken/ to a copy; the tests must fail
make all
```

## Interview questions

1. Why send Gray code across the clock boundary instead of binary?
2. Why does the full check invert the top two bits of the synchronized read pointer, not just the top one?
3. Why is it safe that `w_full` and `r_empty` are late? What would go wrong if they were early?
4. What is the mean time between failures of a two-flop synchronizer, and what makes it better or worse?
5. Why does the depth have to be a power of two for this design? How would you build a 12-deep one?
6. The timing script cuts every path between the clocks. Which crossing paths still matter, and what constraint would you add for them in a real chip?
7. Why does the skid buffer need two registers to keep full throughput with a registered `s_ready`?
8. What does AXI4-Stream require of `tvalid` and `tdata` while `tready` is low, and how does the test check it?
9. How do the two resets interact? What happens if only one side is reset?
10. The formal proof uses a 4-deep FIFO. Why is that convincing for 16, and where could it fall short?

## Things to try

- Change `DEPTH_LOG2` to 3 and rerun `make test timing`. Watch the area and the flop count.
- Write a fourth patch that synchronizes the binary pointer instead of the Gray one. Do the tests catch it? Why or why not?
- Lower `m_clk` in `timing/timing.tcl` until setup slack goes negative, and read the failing path.
