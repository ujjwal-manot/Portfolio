# cpu

The processor at the end of the chain is a 5-stage RV32I core with machine mode. It reads the ADC samples that `fifo_bridge` delivers, runs the filter firmware on them, and sleeps in `wfi` between interrupts. Its code and data live in two IHP SRAM macros. Interfaces, memory map and the cycle timing contract are in `chip.md`.

## Spec

| Item | Value |
|---|---|
| ISA | RV32I + Zicsr, machine mode only (no PMP, no debug triggers) |
| Pipeline | IF, ID, EX, MEM, WB; forwarding from MEM and WB, one-cycle load-use stall, 2-bit predictor with a 16-entry BTB |
| Memory | two `RM_IHPSG13_1P_2048x32_c2_bm_bist` macros, 8 KB of code and 8 KB of data, synchronous: address in one cycle, data in the next; the code macro reads only when the fetch address changes (`imem_en`) |
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

The model itself is checked against Spike (`--isa=rv32i_zicsr_zicntr --priv=m --pmpregions=0 --triggers=0`) on every rv32ui and rv32mi test except breakpoint and pmpaddr, which test the two optional extensions this core leaves out, and on this project's own machine-mode test (`firmware/mi/load_trap_use.S`: misaligned loads whose result the next instruction needs, so a trap and a load-use stall land in the same cycle).

Beyond the RTL:

- **Gate level.** The mapped netlist (IHP cells and the SRAM macros' own models) runs the filter firmware in Icarus. Its outputs must match the Python reference.
- **CDC.** `helpers/cdc_check.py` runs on the RTL and on the cell netlist. The macros count as registers on their A_CLK.
- **Timing.** STA covers three corners with the macros' own liberty.
- **SRAM output hold.** `tests/sram_hold.cir` runs the macro's own sense-amplifier flip-flop, taken from IHP's CDL, at five corners.

## Results

All numbers come from `results/`. Every log there is hashed in `results/summary.json`, together with the sources and helpers that made it.

| Check | Result | Where |
|---|---|---|
| Model against Spike, rv32ui, rv32mi and `firmware/mi` | 56 passed | `results/model_vs_spike.log` |
| Core against the model, the same programs, random start | 56 passed | `results/test_isa.log` |
| Interrupt firmware: timer every 300 cycles, 16 stream samples at random gaps, three windows with interrupts off | 4104 instructions in 6195 cycles, 1788 asleep; interrupts taken {7: 20, 11: 16}; 3 taken with both pending | `results/test_interrupts.log` |
| The same with mtime starting 2000 cycles short of 2^32 | same counts, across the carry into the high word | `results/test_interrupts.log` |
| Filter firmware at full stream rate, each frame within 3200 cycles | frame cycles 2183 2181 2181 2181; IPC 0.969 | `results/test_filter.log` |
| Filter firmware with a gappy stream | IPC 0.867 | `results/test_filter.log` |
| Filter firmware on the mapped netlist | outputs match, same frame cycles | `results/test_power.log` |
| CDC, RTL and cell netlist | 0 problems, 0 waivers | `results/cdc.log`, `results/cdc_cells.log` |
| Setup at 50 MHz, slow / typ / fast (the worst path starts at the stream input, valid 16 ns into the cycle; slow includes the cold-corner derate below) | worst setup slack 1.67 / 2.55 / 3.04 ns; worst setup slack between flops and macros 7.89 / 12.48 / 14.93 ns | `results/timing_*.log` |
| Hold before layout, slow / typ / fast (at the macro data inputs; open until the layout run adds the clock tree and hold repair) | worst hold slack -0.330 / -0.188 / -0.112 ns before layout | `results/timing_*.log` |
| Area after mapping, cells and both macros | chip area 813502 um2 | `results/synth.log` |
| Power in W, filter firmware at full rate, typical corner, zero delay | total 1.24e-02; sequential 8.53e-03; macro 3.42e-03, of which imem 3.16e-03; combinational 4.70e-04 | `results/power.log` |
| The code macro's data output while idle: read a 100 mV split, then 1 ms with the bit lines precharged, both low (either decision), the split reversed, and the sense clock low | every case holds for 1 ms at tt 27 C 1.2 V, ff 125 C 1.32 V, ss -40 C 1.08 V, sf and fs 125 C 1.32 V | `results/sram_hold.log` |

Each macro is 416.64 by 626.7 um in its LEF, 261108 um2, so the two take 522216 of the mapped area. At the slow corner every late cell delay and setup check is raised 1.6%: at 1.08 V the cold slow corner (ss, -40 C), for which IHP ships no library, is that much slower than the 125 C library in power_manager's transistor sweep of inverter, nand2 and nor2 chains (`projects/power_manager/results/speed.log`). The macros' arcs get the same factor; their bit lines need no more, since the bitcell's read current is higher cold (`projects/power_manager/results/bitcell.log`: 0.973 of the bit line time at 1.08 V). The timing rows are not signoff yet. Before layout the synchronized reset is one unbuffered net to about 3000 flops, so `timing.tcl` leaves out paths through it and says so. Hold is reported but not gated. The layout run (`layout/`) builds the reset and clock trees and must gate setup, hold, recovery and removal. The power figure leaves out glitches, because the gate run has no delays. An SDF-timed run is still to come.

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
| code macro enable ignores a redirect | lockstep mismatch in `load_trap_use`: the core ran a stale word where the trap handler belongs | `results/imem_enable_ignores_redirect.log` |

The review of the first version found five one-line bugs that passed every test. At that point the lockstep took mcycle, mip and every IO load from the core, and only checked that an interrupt the core took was enabled. The checks above came from that. The last two rows came from later reviews. The gate-level run found that x0 was read from flops that were never written and had no reset: in silicon x0 would have powered up random, yet all RTL tests passed because Verilator starts every flop at zero. The RTL tests now start from random values; the old RTL fails there at its second instruction. The other was that reset came straight from the pin, against `chip.md`. The `imem_en` copy first passed every test: a redirect can only meet a stall when the load holding up the pipeline traps, and no test did that with a dependent instruction behind it. rv32mi's `lw-misaligned` puts an unrelated instruction between the load and its use. `firmware/mi/load_trap_use.S` was written for that case.

## Design notes

- **Commit point in EX.** Every exception can be known in EX: the load and store address is computed there, and so is the jump target. Traps, interrupts and CSR writes all happen there, and minstret counts there. Instructions already in MEM and WB are older and always finish, so nothing after EX is ever flushed.
- **Synchronous memory.** The fetch address for the next cycle (`pc_next`) and the load or store of the instruction in EX go to the macros, which take them at the closing edge. Data comes back in IF and MEM. That is why the store check looks at the EX cycle.
- **External interrupt is registered.** My first version fed `s_tvalid` straight into the interrupt decision. That put the 16 ns input delay at the head of the redirect path, and setup failed. A flop on the line costs one cycle of interrupt latency, which a level interrupt doesn't notice.
- **Every flop has a reset.** IHP ships no flop without a reset pin, so resetting the register file and the BTB costs only the reset tree. x0 is not stored at all: a read of register 0 gives zero.
- **wfi** commits, then holds the pipeline until mie & mip is non-zero. If MIE is set the interrupt is taken on the next instruction, and mepc points after the wfi.
- **Code macro enable.** The code macro reads only when the fetch address changes (`imem_en = redirect || !(e_hold || stall)`); during a stall or `wfi` the address repeats. On the filter workload this took the code macro from 3.26e-03 W (commit c2563df's `results/power.log`) to 3.16e-03 W, 3%, because at IPC 0.97 the address rarely repeats. The power run has no sleeping workload yet, where the saving would be larger. A first version kept `!run` in the term; the slew of the unbuffered reset net then failed setup at the macro by 1.03 ns, and reset already forces the address to 0, so the term went.
- **The macro must hold its word.** `imem_en` relies on the code macro keeping its data output while idle, for a whole `wfi` sleep if the core wakes without a trap. IHP's datasheet only says the memory is deactivated. The CDL shows the output comes from a sense-amplifier flip-flop whose clock is the read clock inverted, and the read clock only pulses from a clock gated by chip select and read or write. Between reads that clock sits high and the amplifier holds its decision regeneratively, so one internal node is held only while its bit line stays high. `make sram_hold` simulates that flip-flop through 1 ms with the bit lines precharged, both pulled low, and reversed, at five corners. It holds in every case.
- **Data macro enable.** The data macro's A_MEN stays tied high and only A_REN and A_WEN are gated. The macro's liberty charges 0 for a clock edge with A_MEN high and neither read nor write; what remains is the clock pin's own term, 0.1210 with A_MEN high against 0.1176 low, next to 65.1 for a read, so gating A_MEN would buy nothing measurable.
- **Power.** Two thirds of the power is flops, nearly all of it their clock pins toggling every cycle. A clock gate on `sleep` is the next step.

## Not done yet

Layout with the macros (running) and the timed gate run on its SDF, riscv-formal, riscv-dv random programs, the MAC instruction, CoreMark, the BTB/gshare study, and the clock gate on `sleep` with measured power.
