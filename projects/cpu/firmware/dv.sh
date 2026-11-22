#!/bin/bash
# Generates riscv-dv's random programs for its rv32i target (each test named on the command line, ITER iterations from seed SEED, with the Python generator and the packages in third_party/pydeps) and builds each twice like the other tests: at address 0 for this cpu and at 0x8000_0000 for Spike.
set -e
dv=../../third_party/riscv-dv
out=build/dv
mkdir -p $out
for t in "$@"; do
  PYTHONPATH=../../third_party/pydeps:$dv/pygen python3 $dv/run.py --target rv32i --test $t --simulator pyflow --steps gen --iterations $ITER --start_seed $SEED -o $out/gen > $out/gen_$t.log 2>&1
done
cc="riscv64-unknown-elf-gcc -march=rv32i_zicsr -mabi=ilp32 -static -nostdlib -nostartfiles -Wl,--no-warn-rwx-segments -I$dv/user_extension -T firmware/link_env.ld"
for s in $out/gen/asm_test/*.S; do
  n=$(basename $s .S)
  $cc $s -o $out/$n.elf
  $cc -Wl,--defsym=BASE=0x80000000 $s -o $out/${n}_spike.elf
  riscv64-unknown-elf-objcopy -O binary $out/$n.elf $out/$n.bin
  riscv64-unknown-elf-objcopy -O binary $out/${n}_spike.elf $out/${n}_spike.bin
done
echo "built $(ls $out/*_spike.elf | wc -l) riscv-dv programs"
