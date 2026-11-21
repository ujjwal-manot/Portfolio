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

Every test runs the RTL in lockstep with `helpers/cpu_model.py`. Each retired instruction (pc, instruction, destination register and value) must match the model. When the core takes an interrupt it reports it on `retire_intr`; the model replays it, and the test checks that the model had that interrupt enabled and was at the same pc. Two kinds of value depend on timing, not on the program: the cycle counter and mip, and loads from the IO page (timer, stream). For those the model takes the core's value. Everything else is compared.

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
| interrupts taken with mstatus.MIE clear | the core took an interrupt the model has disabled | `results/interrupt_ignores_global_enable.log` |
| mret leaves MIE clear | firmware never finished | `results/mret_leaves_interrupts_off.log` |
| wfi never sleeps | the core never slept in wfi | `results/wfi_never_sleeps.log` |

I expected the mret bug to show as a lockstep mismatch. No instruction in the firmware reads mstatus, though, so the wrong MIE only shows up when the next interrupts never come, and the firmware waits forever. I changed its expected message to match.

## Design notes

- **Commit point in EX.** Every exception can be known in EX: the load and store address is computed there, and so is the jump target. Traps, interrupts and CSR writes all happen there, and minstret counts there. Instructions already in MEM and WB are older and always finish; nothing after EX is ever flushed.
- **External interrupt is registered.** My first version fed `s_tvalid` straight into the interrupt decision. That put a 14 ns input-delay pin at the head of the redirect path, which failed setup by 0.76 ns. A flop on the line fixed it at the cost of one cycle of interrupt latency, which a level interrupt doesn't notice.
- **wfi** commits, then holds the pipeline until mie & mip is non-zero. If MIE is set the interrupt is taken on the next instruction, and mepc points after the wfi.
- **mcycle counts clock cycles**, so it can't match the model's count. That's why reads of it are taken from the core.

## Not done yet

riscv-formal, riscv-dv random programs, the MAC instruction, CoreMark, the BTB/gshare study, layout with SRAM macros, and a clock gate on `sleep` with measured power.
