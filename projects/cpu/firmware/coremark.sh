#!/bin/bash
# Builds CoreMark (PERFORMANCE_RUN seeds, ITER iterations) for the 64 KB test board from the pinned sources and a copy of the barebones port made in build/coremark: uart_send_char stores each character to 0x1000_0108, barebones_clock reads mcycle, CLOCKS_PER_SEC is 1000000 so seconds read as millions of cycles, and there is no floating point, so the code is plain RV32I plus Zicsr with libgcc's multiply and divide.
set -e
src=../../third_party/coremark
out=build/coremark
mkdir -p $out
sed -e '/^#error \\$/d' -e 's|^ *"You must implement a method to measure time.*|    ee_u32 c; __asm__ volatile("csrr %0, mcycle" : "=r"(c)); return c;|' -e '/^ *"Call board initialization routines/d' $src/barebones/core_portme.c > $out/core_portme.c
sed 's|^#error "You must implement the method uart_send_char.*|    *(volatile char *)0x10000108 = c;|' $src/barebones/ee_printf.c > $out/ee_printf.c
cp $src/barebones/core_portme.h $out/core_portme.h
flags="-O2 -march=rv32i_zicsr -mabi=ilp32"
riscv64-unknown-elf-gcc $flags -DSTACK_TOP=0x10000 -c firmware/start.S -o $out/start.o
riscv64-unknown-elf-gcc $flags -nostdlib -nostartfiles -Wl,-N,--no-warn-rwx-segments -T firmware/link.ld -I$out -I$src \
  -include stddef.h -DHAS_TIME_H=0 -DHAS_FLOAT=0 -DMAIN_HAS_NOARGC=1 -DCLOCKS_PER_SEC=1000000 -DPERFORMANCE_RUN=1 -DITERATIONS=$ITER "-DFLAGS_STR=\"$flags\"" \
  $out/start.o $src/core_list_join.c $src/core_main.c $src/core_matrix.c $src/core_state.c $src/core_util.c $out/core_portme.c $out/ee_printf.c -lc -lgcc -o $out/coremark.elf
riscv64-unknown-elf-objcopy -O binary $out/coremark.elf $out/coremark.bin
riscv64-unknown-elf-size $out/coremark.elf
