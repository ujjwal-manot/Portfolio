# cpu commands: make firmware | model | test | filter | timing | broken | all
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
ROOT := $(shell git rev-parse --show-toplevel)
RUN := $(ROOT)/setup/run.sh
SIM ?= verilator
PYTEST := $(RUN) env PYTHONPATH=$(ROOT)/helpers SIM=$(SIM) python3 -m pytest -q -s -p no:cacheprovider
SAVE := $(RUN) python3 $(ROOT)/helpers/save_result.py results/summary.json
LIB := /foss/pdks/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_slow_1p08V_125C.lib
RISCV_TESTS := 3df703cd52d5f0d8224e3c50bf03c6cb70efff98

all: model test filter timing broken

build/riscv-tests/isa/rv32ui/add.S:
	mkdir -p build/riscv-tests
	cd build/riscv-tests && git init -q && git fetch -q --depth 1 https://github.com/riscv-software-src/riscv-tests.git $(RISCV_TESTS) && git checkout -q FETCH_HEAD

firmware: build/riscv-tests/isa/rv32ui/add.S
	$(RUN) firmware/build.sh

model: firmware
	mkdir -p results
	if $(PYTEST) -v tests/test_cpu_model.py > results/model_vs_spike.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) model_vs_spike $$c results/model_vs_spike.log

test: firmware
	mkdir -p results
	if $(PYTEST) tests/test_cpu.py > results/test_rv32ui.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) test_rv32ui $$c results/test_rv32ui.log

filter: firmware
	mkdir -p results
	if $(PYTEST) tests/test_filter.py > results/test_filter.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) test_filter $$c results/test_filter.log

timing:
	mkdir -p build results
	$(RUN) cp $(LIB) build/slow.lib
	if (cd timing && $(RUN) yosys -s synth.ys) > results/synth.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) synth $$c results/synth.log
	if (cd timing && $(RUN) sta -no_init -exit timing.tcl) > results/timing.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) timing $$c results/timing.log

broken: firmware
	mkdir -p results
	for p in broken/*.patch; do n=$$(basename $$p .patch); d=build/$$n; mkdir -p $$d/build; cp -r design tests $$d; \
	  cp build/filter.* $$d/build; ln -sfn $(CURDIR)/build/rv32ui $$d/build/rv32ui; patch -s -d $$d -p1 < $$p; \
	  if (cd $$d && $(PYTEST) -x tests/test_cpu.py tests/test_filter.py) > results/$$n.log 2>&1; then c=1; else c=0; fi; \
	  $(SAVE) broken_$$n $$c results/$$n.log; done

.PHONY: all firmware model test filter timing broken
