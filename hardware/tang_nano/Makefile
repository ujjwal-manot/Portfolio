# Synthesizes, places, routes, packs, and flashes fifo_bridge and cpu onto a Sipeed Tang Nano 20K (GW2AR-18) using Yosys, nextpnr-himbaechel, gowin_pack, and openFPGALoader.
BUILD = build
DEVICE = GW2AR-LV18QN88C8/I7
FAMILY = GW2A-18C
BOARD = tangnano20k
YOSYS ?= yosys
NEXTPNR ?= nextpnr-himbaechel
GOWIN_PACK ?= gowin_pack
LOADER ?= openFPGALoader

RTL = \
	../../projects/fifo_bridge/design/sync2.sv \
	../../projects/fifo_bridge/design/reset_sync.sv \
	../../projects/fifo_bridge/design/async_fifo.sv \
	../../projects/fifo_bridge/design/skid_buffer.sv \
	../../projects/fifo_bridge/design/fifo_bridge.sv \
	../../projects/cpu/design/cpu.sv \
	uart_tx.sv \
	top.sv

.PHONY: all synth pnr bitstream flash test clean

all: $(BUILD)/top.fs

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/top.json: $(RTL) firmware.hex | $(BUILD)
	$(YOSYS) -q -p "read_verilog -sv $(RTL); synth_gowin -top top -json $@"

$(BUILD)/pnr.json: $(BUILD)/top.json tang_nano_20k.cst
	$(NEXTPNR) --json $< --write $@ --device $(DEVICE) --vopt family=$(FAMILY) --vopt cst=tang_nano_20k.cst

$(BUILD)/top.fs: $(BUILD)/pnr.json
	$(GOWIN_PACK) -d $(FAMILY) -o $@ $<

flash: $(BUILD)/top.fs
	$(LOADER) -b $(BOARD) $<

test:
	pytest -q test_firmware.py

clean:
	rm -rf $(BUILD)
