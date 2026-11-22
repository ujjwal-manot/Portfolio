# Misaligned loads whose result the very next instruction needs, so the load-use stall and the trap's redirect come in the same cycle: the handler must run next (not a stale fetch), the load must leave its register alone, and both traps must be taken with cause 4.
#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32M
RVTEST_CODE_BEGIN
  la s0, data
  li s1, 0
  li TESTNUM, 2
  li x14, 7
  lw x14, 1(s0)
  add x13, x14, x14
  li x7, 14
  bne x13, x7, fail
  li TESTNUM, 3
  li x14, 5
  lh x14, 3(s0)
  beq x14, x0, fail
  li x7, 5
  bne x14, x7, fail
  li TESTNUM, 4
  li x7, 2
  bne s1, x7, fail
  TEST_PASSFAIL

  .align 2
  .global mtvec_handler
mtvec_handler:
  csrr t0, mcause
  li t1, CAUSE_MISALIGNED_LOAD
  bne t0, t1, fail
  addi s1, s1, 1
  csrr t0, mepc
  addi t0, t0, 4
  csrw mepc, t0
  mret

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

data:
  .word 0x12345678
  .word 0x9abcdef0

RVTEST_DATA_END
