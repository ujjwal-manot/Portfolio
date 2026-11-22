#!/bin/bash
# Builds the filter firmware (plain, and with -DMAC using the custom-0 multiply-accumulate) and the interrupt firmware, and every rv32ui test (on the small environment in riscv_test.h) and rv32mi test and this project's own machine-mode tests in firmware/mi (on the standard riscv-test-env, which sets up traps) twice: at address 0 for this cpu and at 0x8000_0000 for Spike.
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
ecc="riscv64-unknown-elf-gcc -march=rv32i_zicsr -mabi=ilp32 -nostdlib -nostartfiles -Wl,--no-warn-rwx-segments -T firmware/link_env.ld -Ibuild/riscv-test-env/p -I$src/macros/scalar"
mkdir -p build/rv32mi
for s in $src/rv32mi/*.S; do
  n=$(basename $s .S)
  $ecc -Wl,--defsym=TOHOST=0x10000100 $s -o build/rv32mi/$n.elf
  $ecc -Wl,--defsym=BASE=0x80000000 $s -o build/rv32mi/${n}_spike.elf
  riscv64-unknown-elf-objcopy -O binary build/rv32mi/$n.elf build/rv32mi/$n.bin
  riscv64-unknown-elf-objcopy -O binary build/rv32mi/${n}_spike.elf build/rv32mi/${n}_spike.bin
done
for s in firmware/mi/*.S; do
  n=$(basename $s .S)
  $ecc -Wl,--defsym=TOHOST=0x10000100 $s -o build/rv32mi/$n.elf
  $ecc -Wl,--defsym=BASE=0x80000000 $s -o build/rv32mi/${n}_spike.elf
  riscv64-unknown-elf-objcopy -O binary build/rv32mi/$n.elf build/rv32mi/$n.bin
  riscv64-unknown-elf-objcopy -O binary build/rv32mi/${n}_spike.elf build/rv32mi/${n}_spike.bin
done
$cc -O2 firmware/start.S firmware/filter.c -o build/filter.elf
riscv64-unknown-elf-objcopy -O binary build/filter.elf build/filter.bin
$cc -O2 -DMAC firmware/start.S firmware/filter.c -o build/filter_mac.elf
riscv64-unknown-elf-objcopy -O binary build/filter_mac.elf build/filter_mac.bin
riscv64-unknown-elf-gcc -march=rv32i_zicsr -mabi=ilp32 -nostdlib -nostartfiles -Wl,-N,--no-warn-rwx-segments -T firmware/link.ld firmware/interrupts.S -o build/interrupts.elf
riscv64-unknown-elf-objcopy -O binary build/interrupts.elf build/interrupts.bin
riscv64-unknown-elf-size build/filter.elf build/filter_mac.elf
echo "built $(ls $out/*_spike.elf build/rv32mi/*_spike.elf | wc -l) tests and the filter"
