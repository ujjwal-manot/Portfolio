# cpu

The processor at the end of the chain: a 5-stage RV32I core with machine mode. It reads the ADC samples that `fifo_bridge` delivers, runs the filter firmware on them, and sleeps in `wfi` between interrupts. Interfaces and memory map are in `chip.md`.

## Spec

| Item | Value |
|---|---|
| ISA | RV32I + Zicsr, machine mode only (no PMP, no debug triggers) |
| Pipeline | IF, ID, EX, MEM, WB; forwarding from MEM and WB, one-cycle load-use stall, 2-bit predictor with a 16-entry BTB |
| Traps | illegal instruction, ecall, ebreak, misaligned load, store and jump target; mret |
| Interrupts | timer (mtime >= mtimecmp, cause 7) and external (a stream sample waiting, cause 11), vectored or direct |
| Sleep | `wfi` holds the pipeline and raises `sleep` until an enabled interrupt is pending |
| Clock | 50 MHz at the slow corner (1.08 V, 125 C) |

## How it is checked

Every test runs the RTL in lockstep with `cpu_model.Timed` (`helpers/cpu_model.py`), checked one clock edge at a time by `tests/lockstep.py`:

- **Timing:** MEM and WB never stall, so the instruction in WB spent its EX exactly two edges earlier, and the model is told that cycle.
- **Counters:** from that cycle the model works out mcycle (counting every edge, honouring writes and mcountinhibit), mtime, mtimecmp (from the model's own stores), and mip (from those and the stream valid, registered for a cycle as in the RTL).
- **IO page:** every load from the IO page is answered by address. The only exceptions are the branch and mispredict counters, which belong to the pipeline, not the ISA, and are taken from the core.
- **Interrupts:** the model decides by itself whether an interrupt is due in each EX cycle, and which one (external before timer). The core must take exactly that interrupt in that cycle, and must never retire an instruction while one is due.
- **Instructions and stores:** each retired instruction must match in pc, instruction, destination register and value. Its store must match too: address, byte strobes and stored bytes, seen one edge earlier in MEM. An instruction that doesn't store must leave the strobes low.

The model itself is checked against Spike (`--isa=rv32i_zicsr_zicntr --priv=m --pmpregions=0 --triggers=0`) on every rv32ui and rv32mi test except breakpoint and pmpaddr, which test the two optional extensions this core leaves out.

## Results

All numbers come from `results/`; every log there is hashed in `results/summary.json` together with the sources and helpers that made it.

| Check | Result | Where |
|---|---|---|
| Model against Spike, rv32ui and rv32mi | 55 passed | `results/model_vs_spike.log` |
| Core against the model, rv32ui and rv32mi | 55 passed | `results/test_isa.log` |
| Interrupt firmware: timer every 300 cycles, 16 stream samples at random gaps | 1480 instructions in 4257 cycles, 2554 asleep; interrupts taken {7: 14, 11: 16} | `results/test_interrupts.log` |
| Filter firmware at full stream rate, each frame within 3200 cycles | frame cycles 2183 2181 2181 2181; IPC 0.969 | `results/test_filter.log` |
| Filter firmware with a gappy stream | IPC 0.867 | `results/test_filter.log` |
| Timing at the slow corner, 50 MHz | worst setup slack 3.72 ns, worst hold slack 0.289 ns | `results/timing.log` |
| Area after mapping to IHP cells | chip area 307319.97 um2 | `results/synth.log` |

## Broken copies

Each copy below has one bug put in on purpose and must fail with the message on the first line of its patch. The tests run in the order interrupts, ISA, filter and stop at the first failure.

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

The review of the first version found five one-line bugs that passed every test. Back then the lockstep took mcycle, mip and every IO load from the core, and it only checked that an interrupt the core took was enabled. I rebuilt it as described above, gave the firmware an mcycle read with counting inhibited, an mip read in every handler and a window with interrupts off that leaves both interrupts pending together, and added those bugs here. The fifth one, a timer compare on the low 32 bits only, would need mtime to wrap past 2^32 (86 s at 50 MHz) and is not tested.

## Design notes

- **Commit point in EX.** Every exception can be known in EX: the load and store address is computed there, and so is the jump target. Traps, interrupts and CSR writes all happen there, and minstret counts there. Instructions already in MEM and WB are older and always finish; nothing after EX is ever flushed.
- **External interrupt is registered.** My first version fed `s_tvalid` straight into the interrupt decision. That put a 14 ns input-delay pin at the head of the redirect path, which failed setup by 0.76 ns. A flop on the line fixed it at the cost of one cycle of interrupt latency, which a level interrupt doesn't notice.
- **wfi** commits, then holds the pipeline until mie & mip is non-zero. If MIE is set the interrupt is taken on the next instruction, and mepc points after the wfi.
- **mcycle counts clock cycles**, not instructions, so the plain model (the one checked against Spike) can't match it. Timed works it out from the clock instead.

## Not done yet

riscv-formal, riscv-dv random programs, the MAC instruction, CoreMark, the BTB/gshare study, layout with SRAM macros, and a clock gate on `sleep` with measured power.
