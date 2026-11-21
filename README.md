# EdgeSense-130

A small sensor-to-processor chip on the open IHP SG13G2 130 nm process: an opamp, an 8-bit SAR ADC, a clock-crossing FIFO and a 5-stage RISC-V core, plus five larger extension projects. Everything is simulated, checked and laid out with open-source tools.

## Start

```
setup/start_tools.sh      # starts Docker and pulls hpretl/iic-osic-tools:2026.10
make check_tools          # prints every tool version, fails if something is missing
make all                  # runs every project's tests
make honesty              # checks that every result is backed by a real log
```

On Windows, run the same commands in WSL2. If you are already inside the iic-osic-tools container, `setup/run.sh` runs commands directly.

## Layout

| Folder | What is in it |
|---|---|
| `chip.md` | the whole-chip spec and every block interface |
| `plan.md` | build plan and design reasoning |
| `projects/` | one folder per project: design, tests, broken copies, results |
| `helpers/` | Python scripts that read simulator output and record results |
| `compare_with_papers/` | runs published reference circuits and compares with their published numbers |
| `console/` | 3D web view of the chip and every result |
| `hardware/` | STM32 R-2R DAC and Tang Nano 20K FPGA builds |
| `tracking/` | session log, scorecard and branch decision rules |
| `setup/` | scripts to start and check the tool image |

## How results are kept honest

- Every result in a project's `results/summary.json` lists the raw simulator logs behind it and their SHA-256 hashes. `make honesty` re-hashes them.
- Each project carries three patches in `broken/` that break the design on purpose. Its tests must fail on all three.
- Only the real IHP models are used. Python never simulates a circuit.
