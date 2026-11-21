#!/bin/bash
# Builds the filter firmware, and every rv32ui test twice: at address 0 for this cpu and at 0x8000_0000 for Spike.
set -e
src=build/riscv-tests/isa
out=build/rv32ui
mkdir -p $out
cc="riscv64-unknown-elf-gcc -march=rv32i -mabi=ilp32 -nostdlib -nostartfiles -Wl,-N,--no-warn-rwx-segments -T firmware/link.ld -Ifirmware -I$src/macros/scalar"
for s in $src/rv32ui/*.S; do
  n=$(basename $s .S)
  case $n in fence_i|ma_data) continue;; esac
  $cc $s -o $out/$n.elf
  $cc -Wl,--defsym=BASE=0x80000000 -DRESULT_ADDR=tohost $s -o $out/${n}_spike.elf
  riscv64-unknown-elf-objcopy -O binary $out/$n.elf $out/$n.bin
  riscv64-unknown-elf-objcopy -O binary $out/${n}_spike.elf $out/${n}_spike.bin
done
$cc -O2 firmware/start.S firmware/filter.c -o build/filter.elf
riscv64-unknown-elf-objcopy -O binary build/filter.elf build/filter.bin
riscv64-unknown-elf-size build/filter.elf
echo "built $(ls $out/*_spike.elf | wc -l) tests and the filter"
