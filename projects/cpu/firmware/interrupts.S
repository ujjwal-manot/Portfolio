// Interrupt workout: counts in a loop until 4 timer interrupts (one every 300 cycles) have been taken, then sleeps in wfi until 8 timer interrupts and 16 stream samples (one external interrupt each) have arrived, then writes the sum of the samples to 0x1000_0104 and 1 (pass) to 0x1000_0100.
.equ PERIOD, 300
.section .text.start
.globl _start
_start:
  la t0, handler
  csrw mtvec, t0
  li s0, 0x10000000
  lw t0, 0x20(s0)
  addi t0, t0, PERIOD
  sw t0, 0x28(s0)
  sw zero, 0x2c(s0)
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
sleep:
  wfi
  li t0, 8
  blt s1, t0, sleep
  li t0, 16
  blt s2, t0, sleep
  csrci mstatus, 8
  sw s3, 0x104(s0)
  li t0, 1
  sw t0, 0x100(s0)
1: j 1b

handler:
  csrr a0, mcause
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
  lw a1, 0x28(s0)
  addi a1, a1, PERIOD
  sw a1, 0x28(s0)
  addi s1, s1, 1
  mret
fail:
  li t0, 3
  sw t0, 0x100(s0)
2: j 2b
