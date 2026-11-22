# STM32 Nucleo-H753ZI 8-bit R-2R DAC Bench

Bare-metal firmware and host parser for an 8-bit breadboard R-2R ladder driven and measured by an ST Nucleo-H753ZI (MB1364) using the pinned `arm-none-eabi-gcc` (14.3.rel1), `libopencm3` (`a3977e14519e`), and `OpenOCD` (v0.12.0) tools from `setup/get_tools.sh`.

## Hardware Wiring

| Signal | Nucleo-H753ZI Pin | Value |
|---|---|---|
| DAC bits `[7:0]` (MSB to LSB) | `PF7` down to `PF0` (CN9/CN11/CN12 Morpho) | Push-pull 3.3 V CMOS into 2R legs |
| R-2R ladder output | `PA3` (Arduino `A0`, `ADC1_INP15`) | 0 to 3.3 V analog readback |
| Ladder ground | `GND` | 2R termination to ground at bit 0 |
| Serial console | `PD8` (TX), `PD9` (RX), ST-LINK VCP (`USART3`) | 115200 baud, 8N1 |
| Resistors | 1% metal film | `R = 10 kOhm`, `2R = 20 kOhm` (or two `10 kOhm` in series) |

## Firmware Timing and Design

- Runs from the 64 MHz internal HSI clock out of reset with zero dynamic heap allocation (`malloc`/`free` absent) and zero floating-point math.
- Uses the Cortex-M7 DWT cycle counter (`DWT_CYCCNT`) to pace both the static 256-code ramp (`R <code> <adc16>`) and the 1024-sample coherent sine capture (`S <index> <dac_code> <adc16>`).
- Coherent sine table has `N = 1024` samples and `k = 13` cycles (`gcd(13, 1024) = 1`) paced at `6400` HSI cycles per sample (`fs = 10000 Hz`, `fin = 126.953125 Hz`). All 1024 ADC conversions are stored into a static SRAM buffer (`sine_adc_buf[1024]`) before UART transmission so serial framing adds zero jitter to sample timing.
- `ADC1` runs synchronously at `HCLK / 4 = 16 MHz` (`CKMODE = 11`, below the 20 MHz boost threshold on both Rev Y and Rev V silicon) with 16-bit resolution and linear + offset calibration on boot.

## Build, Flash, and Measure

```bash
# 1. Build firmware (after `make tools` in repo root)
make -C hardware/stm32_dac all

# 2. Flash Nucleo-H753ZI over ST-LINK
make -C hardware/stm32_dac flash

# 3. Capture serial output (115200 8N1) to capture.log, then analyze
python3 hardware/stm32_dac/capture.py capture.log codes.txt
python3 helpers/adc_spectrum.py codes.txt 10000 126.953125
```

## Verification Status

- Host parser and `helpers/adc_spectrum.py` compatibility are verified locally with `pytest -q hardware/stm32_dac/test_capture.py`.
- Firmware compilation (`arm-none-eabi-gcc`) and physical board capture require the Linux tool container (`make tools`) and a wired Nucleo-H753ZI board; no synthetic board measurements are committed.
