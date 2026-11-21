# EdgeSense-130 chip

IHP SG13G2 130 nm, VDD = 1.2 V, all low-voltage devices (`sg13_lv_nmos`, `sg13_lv_pmos`).

```
          0.2 .. 1.0 V                       8-bit codes            AXI4-Stream             AXI4-Stream
sensor ---> [opamp] ---> [adc] -------------------> [fifo_bridge] ----------------> [cpu]
            gain -1      1 MS/s                      10 MHz -> 50 MHz                filter + detector
            about 0.6 V  clk_adc = 10 MHz            16 deep                         clk_sys = 50 MHz
```

## Clocks and resets

| Name | Frequency | Used by |
|---|---|---|
| clk_adc | 10 MHz | adc logic, write side of fifo_bridge |
| clk_sys | 50 MHz | read side of fifo_bridge, cpu |

The two clocks are unrelated. Resets are active low (`rst_n`), asserted asynchronously, released synchronously in each clock domain.

## Signal levels

| Signal | Value |
|---|---|
| Sensor input | 0.2 to 1.0 V, up to 50 kHz |
| VCM (mid-rail reference) | 0.6 V |
| ADC reference | vref_lo = 0.2 V, vref_hi = 1.0 V |
| 1 LSB | 3.125 mV |

## Block interfaces

### opamp

```
.subckt opamp inp inn out vdd vss ibias
```

`ibias` takes a 10 uA reference current into the chip (a current sink to vss inside the opamp).

Test setup: inverting amplifier, Rin = Rf = 20 k, `inp` at 0.6 V, 2.05 pF load. Output = 1.2 V - input.

| Spec | Target |
|---|---|
| DC gain | >= 66 dB |
| GBW | >= 20 MHz |
| Phase margin (beta = 0.5 loop, all corners, Monte Carlo) | >= 60 deg |
| Slew rate | >= 10 V/us |
| Settling, 0.8 V step to 1.56 mV | <= 200 ns |
| Supply current | <= 500 uA |

### adc

Analog parts:

```
.subckt comparator inp inn clk outp outn vdd vss
.subckt cap_dac top vin vcm vref_hi vref_lo samp d7 d6 d5 d4 d3 d2 d1 d0 vdd vss
```

The comparator is a StrongARM latch. It resets while `clk` is low and decides while `clk` is high: `outp` high means `inp > inn`.

The DAC uses 256 unit capacitors of about 8 fF (2.05 pF in total) with bottom-plate sampling:
- While `samp` is high, every bottom plate follows `vin` and the top plate is held at `vcm`.
- After that, bottom plate `k` connects to `vref_hi` when `dk` is 1 and to `vref_lo` when it is 0.

Digital part, `sar_logic.sv`:

```
module sar_logic (
  input  logic       clk, rst_n, comp_out,
  output logic       samp, comp_clk,
  output logic [7:0] dac,
  output logic       m_tvalid,
  input  logic       m_tready,
  output logic [7:0] m_tdata,
  output logic       m_tlast,
  output logic       overflow
);
```

Each sample takes 10 clk_adc cycles:
- 2 cycles with `samp` high.
- 8 bit trials, MSB first. Each trial sets `dac` on the rising edge, the comparator fires in the low half of the cycle, and the bit is kept on the next rising edge.

Every 64th sample sets `m_tlast`. The ADC cannot wait, so if `m_tready` is low when a sample is ready, the sample is dropped and the sticky `overflow` flag is set.

| Spec | Target |
|---|---|
| ENOB (coherent FFT, -0.5 dBFS sine) | >= 7.5 bits |
| DNL / INL | within +-0.5 LSB / +-1 LSB |
| Offset / gain error | within +-1 LSB / +-2 LSB |

### fifo_bridge

```
module fifo_bridge (
  input  logic       s_clk, s_rst_n,
  input  logic       s_tvalid,
  output logic       s_tready,
  input  logic [7:0] s_tdata,
  input  logic       s_tlast,
  input  logic       m_clk, m_rst_n,
  output logic       m_tvalid,
  input  logic       m_tready,
  output logic [7:0] m_tdata,
  output logic       m_tlast
);
```

Inside: `async_fifo` (9 bits wide, 16 deep, Gray-code pointers, two-flop synchronizers), then `skid_buffer` on the read side so `s_tready` and `m_tready` never form a combinational path. No word is ever lost, duplicated or reordered.

### cpu

```
module cpu (
  input  logic        clk, rst_n,
  output logic [31:0] imem_addr,
  input  logic [31:0] imem_data,
  output logic [31:0] dmem_addr, dmem_wdata,
  output logic [3:0]  dmem_wstrb,
  output logic        dmem_read,
  input  logic [31:0] dmem_rdata,
  input  logic        s_tvalid,
  output logic        s_tready,
  input  logic [7:0]  s_tdata,
  input  logic        s_tlast,
  output logic        retire_valid,
  output logic [31:0] retire_pc, retire_instr, retire_rd_data,
  output logic [4:0]  retire_rd
);
```

- RV32I, 5 stages (IF, ID, EX, MEM, WB), with forwarding, a load-use stall and a 2-bit branch predictor with a 16-entry BTB.
- Instruction and data memory are outside the core and read in the same cycle (combinational).
- `retire_*` reports every finished instruction, so a testbench can check each one against `helpers/cpu_model.py`.

Memory map:

| Address | Read | Write |
|---|---|---|
| 0x0000_0000 .. 0x0000_FFFF | instruction and data RAM (64 KB) | RAM |
| 0x1000_0000 | stream: bit 31 = valid, bit 8 = last, bits 7..0 = data; reading pops the word when valid | |
| 0x1000_0010 | cycle counter | |
| 0x1000_0014 | retired instruction counter | |
| 0x1000_0018 | branch counter | |
| 0x1000_001C | mispredict counter | |
| 0x1000_0100 | | test result: 1 = pass, any other value = fail code |

Firmware flips each code back with `code ^ 0xFF`, because the opamp inverts.

| Spec | Target |
|---|---|
| riscv-tests rv32ui | all pass, every retired instruction matches the model |
| Clock | 50 MHz at the slow corner (1.08 V, 125 C) |
| Filter (8-tap FIR + threshold per sample) | <= 3200 cycles per 64-sample frame |

## Why these numbers

See the table in `plan.md`. In short:
- Half an LSB of settling in 200 ns needs tau under 32 ns. Gain -1 halves the loop bandwidth, so GBW must be at least 20 MHz for tau = 16 ns.
- A 0.4 V swing needs 60.2 dB for a quarter-LSB static error. 66 dB leaves room for the slow corners.
- A 64-sample frame every 64 us is 3200 cycles at 50 MHz, which is the filter's budget.
