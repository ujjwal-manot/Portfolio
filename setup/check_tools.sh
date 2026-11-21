#!/bin/bash
# Prints the version of every tool and PDK file the lab needs, and fails if any is missing.
missing=0
for t in ngspice iverilog verilator yosys sby sta openroad librelane magic klayout netgen xschem riscv64-unknown-elf-gcc spike python3; do
  command -v $t >/dev/null || { echo "MISSING tool: $t"; missing=1; }
done
p=$PDK_ROOT/$PDK
for f in libs.tech/ngspice/models/cornerMOSlv.lib libs.tech/ngspice/osdi/psp103.osdi libs.tech/ngspice/.spiceinit \
         libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_slow_1p08V_125C.lib; do
  [ -f "$p/$f" ] || { echo "MISSING file: $p/$f"; missing=1; }
done
[ $missing = 0 ] || exit 1
echo "image $IIC_OSIC_TOOLS_VERSION, pdk $p ($(cat $p/COMMIT 2>/dev/null))"
ngspice -v 2>&1 | grep -m1 -o 'ngspice-[0-9]*'
iverilog -V 2>&1 | head -1
verilator --version
yosys -V
sby --version 2>&1 | head -1
echo "OpenSTA $(sta -version 2>&1 | tail -1)"
echo "OpenROAD $(openroad -version 2>&1 | tail -1)"
librelane --version 2>&1 | grep -m1 LibreLane
echo "magic $(magic --version)"
klayout -v
netgen -batch quit </dev/null 2>&1 | grep -m1 Netgen
timeout 10 xschem -x -q --version </dev/null 2>&1 | head -1
riscv64-unknown-elf-gcc --version | head -1
spike --help 2>&1 | head -1
python3 -c "import cocotb, pyuvm, numpy, scipy; print('cocotb', cocotb.__version__, 'pyuvm', pyuvm.__version__, 'numpy', numpy.__version__, 'scipy', scipy.__version__)"
