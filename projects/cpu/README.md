# cpu

The processor at the end of the chain is a 5-stage RV32I core with machine mode. It reads the ADC samples that `fifo_bridge` delivers, runs the filter firmware on them, and sleeps in `wfi` between interrupts. Its code and data live in two IHP SRAM macros. Interfaces, memory map and the cycle timing contract are in `chip.md`.

## Spec

| Item | Value |
|---|---|
| ISA | RV32I + Zicsr, machine mode only (no PMP, no debug triggers) |
| Pipeline | IF, ID, EX, MEM, WB; forwarding from MEM and WB, one-cycle load-use stall, 2-bit predictor with a 16-entry BTB |
| Memory | two `RM_IHPSG13_1P_2048x32_c2_bm_bist` macros, 8 KB of code and 8 KB of data, synchronous: address in one cycle, data in the next |
| Traps | illegal instruction, ecall, ebreak, misaligned load, store and jump target; mret |
| Interrupts | timer (mtime >= mtimecmp on all 64 bits, cause 7) and external (a stream sample waiting, cause 11), vectored or direct |
| Sleep | `wfi` holds the pipeline and raises `sleep` until an enabled interrupt is pending |
| Reset | asserted at once, released two edges later through `reset_sync` (from fifo_bridge); every flop is reset |
| Clock | 50 MHz at the slow corner (1.08 V, 125 C) |

## How it is checked

Every RTL test runs the core in lockstep with `cpu_model.Timed` (`helpers/cpu_model.py`). `tests/lockstep.py` does the checking, one clock edge at a time:

- **Start state.** Every flop and memory word starts at a random value (Verilator `--x-initial unique` with `+verilator+rand+reset+2`), as silicon does. Verilator's default is all zeros.
- **Timing.** MEM and WB never stall, so the instruction in WB spent its EX exactly two edges earlier. The model is told that cycle.
- **Counters and timer.** From that cycle the model works out every counter on its own: mcycle (every edge, honouring writes and mcountinhibit), mtime, mtimecmp (from its own stores), mip (from those and the stream valid, registered for a cycle as in the RTL), and the branch and mispredict counters (from its own branches and the pc fetched after each one).
- **Interrupts.** The model decides on its own whether an interrupt is due in each EX cycle, and which one (external before timer). The core must take exactly that interrupt in that cycle, and must never retire an instruction while one is due.
- **Instructions and stores.** Each retired instruction must match in pc, instruction, destination register and value. Its store must match too: address, byte strobes and stored bytes, as driven to the data macro in its EX cycle. An instruction that doesn't store must leave the strobes low.

The model itself is checked against Spike (`--isa=rv32i_zicsr_zicntr --priv=m --pmpregions=0 --triggers=0`) on every rv32ui and rv32mi test except breakpoint and pmpaddr, which test the two optional extensions this core leaves out.

Beyond the RTL:

- **Gate level.** The mapped netlist (IHP cells and the SRAM macros' own models) runs the filter firmware in Icarus. Its outputs must match the Python reference.
- **CDC.** `helpers/cdc_check.py` runs on the RTL and on the cell netlist. The macros count as registers on their A_CLK.
- **Timing.** STA covers three corners with the macros' own liberty.

## Results

All numbers come from `results/`. Every log there is hashed in `results/summary.json`, together with the sources and helpers that made it.

| Check | Result | Where |
|---|---|---|
| Model against Spike, rv32ui and rv32mi | 55 passed | `results/model_vs_spike.log` |
| Core against the model, rv32ui and rv32mi, random start | 55 passed | `results/test_isa.log` |
| Interrupt firmware: timer every 300 cycles, 16 stream samples at random gaps, three windows with interrupts off | 4104 instructions in 6195 cycles, 1788 asleep; interrupts taken {7: 20, 11: 16}; 3 taken with both pending | `results/test_interrupts.log` |
| The same with mtime starting 2000 cycles short of 2^32 | same counts, across the carry into the high word | `results/test_interrupts.log` |
| Filter firmware at full stream rate, each frame within 3200 cycles | frame cycles 2183 2181 2181 2181; IPC 0.969 | `results/test_filter.log` |
| Filter firmware with a gappy stream | IPC 0.867 | `results/test_filter.log` |
| Filter firmware on the mapped netlist | outputs match, same frame cycles | `results/test_power.log` |
| CDC, RTL and cell netlist | 0 problems, 0 waivers | `results/cdc.log`, `results/cdc_cells.log` |
| Setup at 50 MHz, slow / typ / fast | 1.68 / 2.53 / 3.03 ns (the stream input, 16 ns into the cycle); between flops and macros 7.75 / 12.26 / 14.77 ns | `results/timing_*.log` |
| Hold before layout, slow / typ / fast | -0.37 / -0.20 / -0.12 ns at the macro data inputs (open: no clock tree or hold repair yet; the layout run must close it) | `results/timing_*.log` |
| Area after mapping | 814150 um2, of which the two macros are 522216 | `results/synth.log` |
| Power, filter firmware at full rate, typical corner, zero delay | 12.5 mW: flops 8.5, macros 3.5 (code macro 3.3), logic 0.5 | `results/power.log` |

The timing rows are not signoff yet. Before layout the synchronized reset is one unbuffered net to about 3000 flops, so `timing.tcl` leaves out paths through it and says so. Hold is reported but not gated. The layout run (`layout/`) builds the reset and clock trees and must gate setup, hold, recovery and removal. The power figure leaves out glitches, because the gate run has no delays. An SDF-timed run is still to come.

## Broken copies

Each copy below has one bug put in on purpose, and must fail with the message on the first line of its patch. The tests run in the order interrupts, ISA, filter and stop at the first failure. A patch with `Run: cdc` runs the CDC check instead.

| Bug | Caught by | Where |
|---|---|---|
| no flush after a mispredict | lockstep mismatch | `results/no_flush_after_mispredict.log` |
| no forwarding from MEM | lockstep mismatch | `results/no_forwarding_from_mem.log` |
| no load-use stall | lockstep mismatch | `results/no_load_use_stall.log` |
| mepc points past the trapped instruction | lockstep mismatch | `results/mepc_skips_trapped_instruction.log` |
| interrupts taken with mstatus.MIE clear | the core took an interrupt when the model had none due | `results/interrupt_ignores_global_enable.log` |
| mret leaves MIE clear | an interrupt was due but the core retired an instruction | `results/mret_leaves_interrupts_off.log` |
| interrupt priority inverted | the core took the timer interrupt while the model had the external one due | `results/interrupt_priority_inverted.log` |
| mip reads with MEIP and MTIP swapped | lockstep mismatch on the handler's mip read | `results/mip_bits_swapped.log` |
| mcountinhibit.CY ignored | lockstep mismatch on an mcycle read with counting inhibited | `results/mcountinhibit_cycle_ignored.log` |
| mtime reads 64 too high | lockstep mismatch on the mtime load | `results/mtime_read_off_by_64.log` |
| byte stores ignore the address offset | the core's store differs from the model's | `results/byte_store_ignores_offset.log` |
| wfi never sleeps | the core never slept in wfi | `results/wfi_never_sleeps.log` |
| branch counter misses taken branches | lockstep mismatch on the counter load | `results/branch_counter_misses_taken.log` |
| mispredict counter counts traps | lockstep mismatch on the counter load | `results/mispredict_counter_counts_traps.log` |
| timer compares the low word only | the wrap test fails | `results/timer_compares_low_word.log` |
| x0 read from the register file | lockstep mismatch: x0 holds a random value | `results/x0_read_from_register_file.log` |
| reset released straight from the pin | the CDC check: raw reset on every flop | `results/reset_not_synchronized.log` |

The review of the first version found five one-line bugs that passed every test. At that point the lockstep took mcycle, mip and every IO load from the core, and only checked that an interrupt the core took was enabled. The checks above came from that. The last two rows came from later reviews. The gate-level run found that x0 was read from flops that were never written and had no reset: in silicon x0 would have powered up random, yet all RTL tests passed because Verilator starts every flop at zero. The RTL tests now start from random values; the old RTL fails there at its second instruction. The other was that reset came straight from the pin, against `chip.md`.

## Design notes

- **Commit point in EX.** Every exception can be known in EX: the load and store address is computed there, and so is the jump target. Traps, interrupts and CSR writes all happen there, and minstret counts there. Instructions already in MEM and WB are older and always finish, so nothing after EX is ever flushed.
- **Synchronous memory.** The fetch address for the next cycle (`pc_next`) and the load or store of the instruction in EX go to the macros, which take them at the closing edge. Data comes back in IF and MEM. That is why the store check looks at the EX cycle.
- **External interrupt is registered.** My first version fed `s_tvalid` straight into the interrupt decision. That put the 16 ns input delay at the head of the redirect path, and setup failed. A flop on the line costs one cycle of interrupt latency, which a level interrupt doesn't notice.
- **Every flop has a reset.** IHP ships no flop without a reset pin, so resetting the register file and the BTB costs only the reset tree. x0 is not stored at all: a read of register 0 gives zero.
- **wfi** commits, then holds the pipeline until mie & mip is non-zero. If MIE is set the interrupt is taken on the next instruction, and mepc points after the wfi.
- **Power.** Two thirds of the power is flops, nearly all of it their clock pins toggling every cycle, and the code macro reads every cycle, even while the core sleeps. A clock gate on `sleep` and a read enable on the code macro are the obvious next steps.

## Not done yet

Layout with the macros (running) and the timed gate run on its SDF, riscv-formal, riscv-dv random programs, the MAC instruction, CoreMark, the BTB/gshare study, and the clock gate on `sleep` with measured power.
