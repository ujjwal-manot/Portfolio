# EdgeSense-130

A chip design lab on the open IHP SG13G2 130 nm SiGe BiCMOS process, split evenly across three tracks. Everything is simulated, checked, signed off and laid out with open-source tools.

| Digital VLSI | Analog VLSI | Analog/mixed-signal |
|---|---|---|
| fifo_bridge: clock-crossing block | opamp: two-stage opamp | adc: 8-bit SAR ADC |
| cpu: 5-stage RISC-V | bandgap_ldo: reference and regulator | power_manager: digital LDO, DVFS, droop response |
| tensor_core: BF16/FP8/MX systolic array | serdes_frontend: SiGe transmitter and equalizer | serdes_link: equalization, clock recovery, NRZ and PAM4 |
| coherent_noc: 4 cores, MESI, mesh network | lc_vco: 10 GHz oscillator | frac_n_pll: fractional-N synthesizer |

`whole_chip` joins the core blocks of all three tracks in one mixed-signal simulation and one layout. See `plan.md` for the full plan.

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
| `console/` | read-only viewer: schematics, layouts, waveforms, results and a 3D die |
| `hardware/` | STM32 R-2R DAC and Tang Nano 20K FPGA builds |
| `tracking/` | session log and the time split across the three tracks |
| `setup/` | scripts to start and check the tool image |

## How results are kept honest

- Every result in a project's `results/summary.json` lists the raw simulator logs behind it and their SHA-256 hashes. `make honesty` re-hashes them.
- Each project carries three patches in `broken/` that break the design on purpose. Its tests must fail on all three.
- Only the real IHP models are used. Python never simulates a circuit.
- Every behavioral model is checked against the transistor circuit it stands for before a system result uses it.
