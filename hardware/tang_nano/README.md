# Tang Nano 20K (GW2AR-18) FPGA Target

Synthesizable open-source FPGA wrapper running `projects/fifo_bridge` and `projects/cpu` together on a Sipeed Tang Nano 20K (`GW2AR-LV18QN88C8/I7`) using Yosys, `nextpnr-himbaechel` (`nextpnr-0.11.1`), `apicula` (`0.35`, `gowin_pack`), and `openFPGALoader` (`v1.2.0`).

## Pinout (`tang_nano_20k.cst`)

| Signal | FPGA Pin | Value |
|---|---|---|
| `clk` | `4` | 27 MHz onboard oscillator (3.3 V) |
| `btn1` | `88` | User button S1, active-high reset (`rst_n = !btn1`) |
| `uart_tx` | `69` | BL616 USB-UART bridge TX, 115200 baud 8N1 |
| `led[0]` | `15` | Heartbeat (`~hb_cnt[23]`, active-low) |
| `led[1]` | `16` | CPU `sleep` indicator (active-low) |
| `led[2]` | `17` | CPU `retire_valid` indicator (active-low) |
| `led[3]` | `18` | UART TX busy indicator (active-low) |
| `led[4]` | `19` | `fifo_bridge` `m_tvalid` indicator (active-low) |
| `led[5]` | `20` | Reset state indicator (active-low) |

## Architecture and Memory Map

- **Dual-clock CDC:** `top.sv` derives a 6.75 MHz sample clock (`clk / 4`) for `fifo_bridge.s_clk` while `fifo_bridge.m_clk` and `cpu.clk` run on the 27 MHz board clock, exercising the full asynchronous Gray-code FIFO and reset synchronizers on silicon.
- **Memories:** 1024 x 32 synchronous instruction BRAM (loaded from `firmware.hex` via `$readmemh`) and 1024 x 32 synchronous byte-enabled data BRAM matching `cpu.sv`'s 1-cycle synchronous SRAM interface.
- **MMIO:**
  - `0x1000_0000`: `fifo_bridge` stream input (internal to `cpu.sv`, `{s_tvalid, 22'b0, s_tlast, s_tdata}`).
  - `0x2000_0000`: UART TX byte register (write `[7:0]` triggers `uart_tx`).
  - `0x2000_0004`: UART status register (read bit 0 = `uart_busy`).
- **Boot Firmware (`firmware.hex`):** 30-instruction RV32I loop that polls `0x1000_0000`, undoes the opamp inversion (`code ^ 0xFF`), accumulates 64-sample frames until `tlast`, computes the frame mean (`sum >> 6`), and transmits two uppercase ASCII hex digits plus `\r\n` over UART.

## Build, Test, and Flash

```bash
# Verify boot firmware bit-exact against helpers/cpu_model.py
make -C hardware/tang_nano test

# Synthesize, place and route, and pack bitstream (inside Linux tool container)
make -C hardware/tang_nano all

# Flash Tang Nano 20K over USB
make -C hardware/tang_nano flash
```

## Verification Status

- `firmware.hex` is verified against `helpers/cpu_model.py` (`pytest -q hardware/tang_nano/test_firmware.py`).
- Gowin synthesis (`yosys`), place-and-route (`nextpnr-himbaechel`), bitstream packing (`gowin_pack`), and physical board UART capture require the Linux container toolchain and a connected Tang Nano 20K; no synthetic synthesis or board logs are committed.
