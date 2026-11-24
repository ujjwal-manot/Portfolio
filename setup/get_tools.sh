#!/bin/bash
# Fetches every pinned extra from plan.md into third_party/ at its exact tag or commit, the two binary releases checked against the SHA-256 recorded on their first download, and the Python packages in setup/pydeps.txt (PIP_CERT passed through for a proxy that re-signs TLS); stops on anything that cannot be fetched or does not match.
set -eo pipefail
cd "$(dirname "$0")/.."
mkdir -p third_party
while read -r name url ref; do
  d=third_party/$name
  if [ ! -d "$d/.git" ]; then git clone -q --filter=blob:none "$url" "$d"; fi
  git -C "$d" -c advice.detachedHead=false checkout -q "$ref"
  echo "$name $ref $(git -C "$d" rev-parse --short=12 HEAD)"
done <<'EOF'
uvm-core https://github.com/accellera-official/uvm-core 2020.3.1
bitwuzla https://github.com/bitwuzla/bitwuzla 0.8.2
boolector https://github.com/Boolector/boolector 3.2.4
riscv-formal https://github.com/YosysHQ/riscv-formal c992aa61fdfe
riscv-dv https://github.com/chipsalliance/riscv-dv f557b89ed688
riscv-tests https://github.com/riscv-software-src/riscv-tests 3df703cd52d5
riscv-arch-test https://github.com/riscv-non-isa/riscv-arch-test 3.10.0
coremark https://github.com/eembc/coremark 1f483d5b8316
embench-iot https://github.com/embench/embench-iot 09c2ed8c3b70
softfloat https://github.com/ucb-bar/berkeley-softfloat-3 07ebd29db0cf
testfloat https://github.com/ucb-bar/berkeley-testfloat-3 a9c849f1b0eb
adc-survey https://github.com/bmurmann/ADC-survey 00b4b855de5c
pybert https://github.com/capn-freako/PyBERT v11.2.0
tt-support-tools https://github.com/TinyTapeout/tt-support-tools 0922544e6c7f
nextpnr https://github.com/YosysHQ/nextpnr nextpnr-0.11.1
apicula https://github.com/YosysHQ/apicula 0.35
openfpgaloader https://github.com/trabucayre/openFPGALoader v1.2.0
libopencm3 https://github.com/libopencm3/libopencm3 a3977e14519e
openocd https://github.com/openocd-org/openocd v0.12.0
EOF
while read -r name sum url; do
  f=third_party/$(basename "$url")
  [ -f "$f" ] || { curl -fsSL -o "$f.part" "$url"; mv "$f.part" "$f"; }
  echo "$sum  $f" | sha256sum -c --quiet
  [ -d "third_party/$name" ] || { mkdir -p "third_party/$name"; tar -xJf "$f" -C "third_party/$name" --strip-components=1; }
  echo "$name $(basename "$url") sha256 ok"
done <<'EOF'
arm-gnu-toolchain 8f6903f8ceb084d9227b9ef991490413014d991874a1e34074443c2a72b14dbd https://developer.arm.com/-/media/Files/downloads/gnu/14.3.rel1/binrel/arm-gnu-toolchain-14.3.rel1-x86_64-arm-none-eabi.tar.xz
node 60e3b0a8500819514aca603487c254298cd776de0698d3cd08f11dba5b8289a8 https://nodejs.org/dist/v24.11.1/node-v24.11.1-linux-x64.tar.xz
EOF
[ -d third_party/pydeps/vsc ] || setup/run.sh env ${PIP_CERT:+PIP_CERT=$PIP_CERT} python3 -m pip install -q --no-deps --target third_party/pydeps -r setup/pydeps.txt
echo "pydeps $(grep -c '==' setup/pydeps.txt) packages"
