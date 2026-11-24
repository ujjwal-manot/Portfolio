// Startup: stack at the top of the 8 KB data memory, run main, then report pass at 0x1000_0100.
.section .text.start
.globl _start
_start:
  li sp, 0x2000
  call main
  li t0, 0x10000100
  li t1, 1
  sw t1, 0(t0)
1: j 1b
