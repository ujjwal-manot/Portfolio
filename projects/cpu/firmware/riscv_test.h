// Minimal riscv-tests environment for this cpu: code at address 0, result written to 0x1000_0100 (1 means pass), or to tohost for Spike.
#ifndef RESULT_ADDR
#define RESULT_ADDR 0x10000100
#endif
#define RVTEST_RV32U .macro init; .endm
#define RVTEST_RV64U RVTEST_RV32U
#define TESTNUM gp
#define RVTEST_CODE_BEGIN .text; .globl _start; _start: li TESTNUM, 0;
#define RVTEST_CODE_END
#define RVTEST_PASS lui t6, %hi(RESULT_ADDR); li t5, 1; sw t5, %lo(RESULT_ADDR)(t6); 1: j 1b;
#define RVTEST_FAIL lui t6, %hi(RESULT_ADDR); slli t5, TESTNUM, 1; ori t5, t5, 1; sw t5, %lo(RESULT_ADDR)(t6); 1: j 1b;
#define RVTEST_DATA_BEGIN .data; .align 6; .globl tohost; tohost: .word 0, 0; .globl fromhost; fromhost: .word 0, 0; .align 4;
#define RVTEST_DATA_END
