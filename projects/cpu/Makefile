# cpu commands: make firmware | model | test | interrupts | filter | timing | cdc | power | sram_hold | broken | all
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
ROOT := $(shell git rev-parse --show-toplevel)
RUN := $(ROOT)/setup/run.sh
SIM ?= verilator
PYTEST := $(RUN) env PYTHONPATH=$(ROOT)/helpers SIM=$(SIM) python3 -m pytest -q -s -p no:cacheprovider
SAVE := $(RUN) python3 $(ROOT)/helpers/save_result.py results/summary.json
PY := $(RUN) env PYTHONPATH=$(ROOT)/helpers python3
LIB := /foss/pdks/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_slow_1p08V_125C.lib
RISCV_TESTS := 3df703cd52d5f0d8224e3c50bf03c6cb70efff98
RISCV_TEST_ENV := 6de71edb142be36319e380ce782c3d1830c65d68
SRAM_LIB := /foss/pdks/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_2048x32_c2_bm_bist_slow_1p08V_125C.lib
STREAM := s_tvalid=clk s_tdata=clk s_tlast=clk
cdc_rtl = $(RUN) yosys -q -p "read_verilog -sv $(1)/design/cpu.sv $(ROOT)/projects/fifo_bridge/design/reset_sync.sv; prep -flatten -top cpu; memory_map; opt_clean; write_json $(1)/build/cdc.json" && \
  $(RUN) python3 $(ROOT)/helpers/cdc_check.py $(1)/build/cdc.json cpu cdc/waivers.txt $(STREAM) imem_data=clk dmem_rdata=clk

all: model test interrupts filter timing cdc power sram_hold broken
HOLD_CORNERS := tt_27_1v2 ff_125_1v32 ss_m40_1v08 sf_125_1v32 fs_125_1v32
HOLD := $(foreach c,$(HOLD_CORNERS),build/sram_hold/$(c)/hold.txt)

build/sram_hold/%/hold.txt: tests/sram_hold.cir
	mkdir -p $(@D)
	cp $< $(@D)
	$(RUN) bash -c 'sed -n "/^.SUBCKT RSC_IHPSG13_DFPQD_MSAFFX2 /,/^.ENDS/p" $$PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_sram/cdl/RM_IHPSG13_1P_2048x32_c2_bm_bist.cdl' | sed 's/^M/XM/; s/ nrd=0//; s/ nrs=0//; s/^+ *$$//' > $(@D)/msaff.cir
	printf '.lib cornerMOSlv.lib mos_%s\n.temp %s\n.param vsupply=%s\n' $$(echo $* | cut -d_ -f1) $$(echo $* | cut -d_ -f2 | tr m -) $$(echo $* | cut -d_ -f3 | tr v .) > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b sram_hold.cir > hold.log 2>&1

sram_hold: $(HOLD)
	mkdir -p results
	for f in $(HOLD); do cp $$f results/sram_hold_$$(basename $$(dirname $$f)).txt; done
	if $(PY) $(ROOT)/helpers/sram_results.py results/sram_hold_*.txt > results/sram_hold.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) sram_hold $$c results/sram_hold.log results/sram_hold_*.txt

build/riscv-tests/isa/rv32ui/add.S:
	mkdir -p build/riscv-tests
	cd build/riscv-tests && git init -q && git fetch -q --depth 1 https://github.com/riscv-software-src/riscv-tests.git $(RISCV_TESTS) && git checkout -q FETCH_HEAD

build/riscv-test-env/p/riscv_test.h:
	mkdir -p build/riscv-test-env
	cd build/riscv-test-env && git init -q && git fetch -q --depth 1 https://github.com/riscv/riscv-test-env.git $(RISCV_TEST_ENV) && git checkout -q FETCH_HEAD

firmware: build/riscv-tests/isa/rv32ui/add.S build/riscv-test-env/p/riscv_test.h
	$(RUN) firmware/build.sh

model: firmware
	mkdir -p results
	if $(PYTEST) -v tests/test_cpu_model.py > results/model_vs_spike.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) model_vs_spike $$c results/model_vs_spike.log

test: firmware
	mkdir -p results
	if $(PYTEST) tests/test_cpu.py > results/test_isa.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) test_isa $$c results/test_isa.log

interrupts: firmware
	mkdir -p results
	if $(PYTEST) tests/test_interrupts.py > results/test_interrupts.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) test_interrupts $$c results/test_interrupts.log

filter: firmware
	mkdir -p results
	if $(PYTEST) tests/test_filter.py > results/test_filter.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) test_filter $$c results/test_filter.log

timing:
	mkdir -p build results
	$(RUN) cp $(LIB) build/slow.lib
	if (cd timing && $(RUN) yosys -s synth.ys) > results/synth.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) synth $$c results/synth.log
	for k in slow typ fast; do if (cd timing && $(RUN) env CORNER=$$k sta -no_init -exit timing.tcl) > results/timing_$$k.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) timing_$$k $$c results/timing_$$k.log; done

broken: firmware
	mkdir -p results
	for p in broken/*.patch; do n=$$(basename $$p .patch); d=build/$$n; mkdir -p $$d/build; cp -r design tests $$d; \
	  cp build/filter.* build/interrupts.* $$d/build; ln -sfn $(CURDIR)/build/rv32ui $$d/build/rv32ui; ln -sfn $(CURDIR)/build/rv32mi $$d/build/rv32mi; \
	  patch -s -F0 -d $$d -p1 < $$p; want=$$(sed -n '1s/^Expected failure: //p' $$p); run=$$(sed -n '2s/^Run: //p' $$p); \
	  if [ "$$run" = cdc ]; then if ($(call cdc_rtl,$$d)) > results/$$n.log 2>&1; then c=1; elif grep -qF -- "$$want" results/$$n.log; then c=0; else c=2; fi; \
	  elif (cd $$d && $(PYTEST) -x tests/test_interrupts.py tests/test_cpu.py tests/test_filter.py) > results/$$n.log 2>&1; then c=1; \
	  elif [ -n "$$want" ] && grep -qF -- "$$want" results/$$n.log; then c=0; else c=2; fi; \
	  $(SAVE) broken_$$n $$c results/$$n.log; done

power: timing firmware
	mkdir -p results
	if $(PYTEST) tests/test_power.py > results/test_power.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) test_power $$c results/test_power.log
	$(RUN) fst2vcd -f build/icarus_cpu_top_board_test_power_FUNCTIONAL/cpu_top_board.fst -o build/cpu_gates.vcd > /dev/null
	if (cd timing && $(RUN) sta -no_init -exit power.tcl) > results/power.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) power $$c results/power.log

cdc: timing
	mkdir -p results
	if ($(call cdc_rtl,.)) > results/cdc.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) cdc $$c results/cdc.log
	$(RUN) yosys -q -p 'read_liberty -lib build/slow.lib; read_liberty -lib $(SRAM_LIB); read_verilog build/cpu_cells.v; hierarchy -top cpu_top; write_json build/cdc_cells.json'
	if $(RUN) python3 $(ROOT)/helpers/cdc_check.py build/cdc_cells.json cpu_top cdc/waivers.txt $(STREAM) > results/cdc_cells.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) cdc_cells $$c results/cdc_cells.log

.PHONY: all firmware model test interrupts filter timing cdc power sram_hold broken
