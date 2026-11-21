# fifo_bridge commands: make test | formal | timing | broken | all
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
ROOT := $(shell git rev-parse --show-toplevel)
RUN := $(ROOT)/setup/run.sh
SIM ?= verilator
PYTEST := $(RUN) env PYTHONPATH=$(ROOT)/helpers SIM=$(SIM) python3 -m pytest -q -s -p no:cacheprovider
SAVE := $(RUN) python3 $(ROOT)/helpers/save_result.py results/summary.json
LIB := /foss/pdks/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_slow_1p08V_125C.lib

all: test formal timing broken

test:
	mkdir -p results
	for t in async_fifo skid_buffer fifo_bridge; do \
	  if $(PYTEST) tests/test_$$t.py > results/test_$$t.log 2>&1; then c=0; else c=$$?; fi; \
	  $(SAVE) test_$$t $$c results/test_$$t.log; done

formal:
	mkdir -p build results
	for t in fifo_proof skid_proof bridge_check fifo_reach skid_reach bridge_reach; do \
	  if (cd formal && $(RUN) sby -f --prefix ../build/formal fifo_rules.sby $$t) > results/formal_$$t.log 2>&1; then c=0; else c=$$?; fi; \
	  $(SAVE) formal_$$t $$c results/formal_$$t.log; done

timing:
	mkdir -p build results
	$(RUN) cp $(LIB) build/slow.lib
	if (cd timing && $(RUN) yosys -s synth.ys) > results/synth.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) synth $$c results/synth.log
	if (cd timing && $(RUN) sta -no_init -exit timing.tcl) > results/timing.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) timing $$c results/timing.log

broken:
	mkdir -p results
	for p in broken/*.patch; do n=build/$$(basename $$p .patch); mkdir -p $$n; cp -r design tests $$n; \
	  patch -s -d $$n -p1 < $$p; \
	  if (cd $$n && $(PYTEST) tests) > results/$$(basename $$p .patch).log 2>&1; then c=1; else c=0; fi; \
	  $(SAVE) broken_$$(basename $$p .patch) $$c results/$$(basename $$p .patch).log; done

.PHONY: all test formal timing broken
