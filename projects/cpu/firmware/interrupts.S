// Interrupt workout: reads mcycle with mcountinhibit set and cleared, counts in a loop until 4 timer interrupts (one every 300 cycles, mtimecmp moved on all 64 bits, writing the low word as all ones first) have been taken, keeps interrupts off three times for 400, 250 and 550 loop turns so the timer and a stream sample end up pending together, then sleeps in wfi until 8 timer interrupts and 16 stream samples (one external interrupt each, mip read in every handler) have arrived, sleeps once more with interrupts masked (the timer wakes it without a trap) and checks that the register written just before that wfi reads back right after it, reads the branch and mispredict counters, and writes the sum of the samples to 0x1000_0104 and 1 (pass) to 0x1000_0100.
.equ PERIOD, 300
.section .text.start
.globl _start
_start:
  la t0, handler
  csrw mtvec, t0
  li s0, 0x10000000
  csrsi mcountinhibit, 1
  csrr a3, mcycle
  nop
  csrr a4, mcycle
  csrci mcountinhibit, 1
  csrr a5, mcycle
  lw s6, 0x24(s0)
  lw s5, 0x20(s0)
  jal ra, advance
  li t0, 0x880
  csrw mie, t0
  li s1, 0
  li s2, 0
  li s3, 0
  li s4, 0
  csrsi mstatus, 8
work:
  addi s4, s4, 1
  li t0, 4
  blt s1, t0, work
  li t0, 400
  jal ra, holdoff
  li t0, 250
  jal ra, holdoff
  li t0, 550
  jal ra, holdoff
sleep:
  wfi
  li t0, 8
  blt s1, t0, sleep
  li t0, 16
  blt s2, t0, sleep
  csrci mstatus, 8
  li t1, 9
  wfi
  mv t2, t1
  li t0, 9
  bne t2, t0, fail
  lw a6, 0x18(s0)
  lw a7, 0x1c(s0)
  sw s3, 0x104(s0)
  li t0, 1
  sw t0, 0x100(s0)
1: j 1b

holdoff:
  csrci mstatus, 8
2: addi t0, t0, -1
  bnez t0, 2b
  csrsi mstatus, 8
  ret

advance:
  addi a1, s5, PERIOD
  sltu a0, a1, s5
  add s6, s6, a0
  mv s5, a1
  li a0, -1
  sw a0, 0x28(s0)
  sw s6, 0x2c(s0)
  sw s5, 0x28(s0)
  ret

handler:
  csrr a0, mcause
  csrr a2, mip
  bgez a0, fail
  andi a0, a0, 31
  li a1, 7
  beq a0, a1, timer
  lw a1, 0(s0)
  andi a1, a1, 255
  add s3, s3, a1
  addi s2, s2, 1
  mret
timer:
  mv s7, ra
  jal ra, advance
  mv ra, s7
  addi s1, s1, 1
  mret
fail:
  li t0, 3
  sw t0, 0x100(s0)
3: j 3b
