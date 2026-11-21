# adc commands: make sar | logic | decide | offset | levels | convert | broken | all
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
ROOT := $(shell git rev-parse --show-toplevel)
RUN := $(ROOT)/setup/run.sh
PY := $(RUN) env PYTHONPATH=$(ROOT)/helpers python3
PYTEST := $(RUN) env PYTHONPATH=$(ROOT)/helpers python3 -m pytest -q -s -p no:cacheprovider
SAVE := $(RUN) python3 $(ROOT)/helpers/save_result.py results/summary.json
PROCESS := tt ss ff sf fs
TEMPS := m40 27 125
VOLTS := min nom hi
VOLT_min := 1.16
VOLT_nom := 1.2
VOLT_hi := 1.32
PASSIVE_tt := typ
PASSIVE_sf := typ
PASSIVE_fs := typ
PASSIVE_ss := wcs
PASSIVE_ff := bcs
DECIDE := $(foreach p,$(PROCESS),$(foreach t,$(TEMPS),$(foreach v,$(VOLTS),build/decide/$(p)_$(t)_$(v)/decide.txt)))
OFFSET := $(foreach n,$(shell seq 1 100),build/offset/$(n)/offset.txt)
LEVELS := $(foreach p,$(PROCESS),build/levels/$(p)_27_nom/dac_levels.txt) $(foreach n,$(shell seq 1 20),build/levels/mc$(n)/dac_levels.txt)
CONVERT := $(foreach p,$(PROCESS),$(foreach t,$(TEMPS),build/convert/$(p)_$(t)_nom/convert.txt))
COMPARATOR := design/comparator.cir design/comparator_sizes.inc
DAC := design/cap_dac.cir design/cap_dac_sizes.inc

all: sar logic decide offset levels convert broken

sar:
	mkdir -p results
	if $(PYTEST) tests/test_sar_logic.py -k "not cells" > results/test_sar_logic.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) test_sar_logic $$c results/test_sar_logic.log

logic:
	mkdir -p build results
	$(RUN) bash -c 'cp /foss/pdks/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib build/typ.lib'
	if (cd logic && $(RUN) yosys -s synth.ys) > results/logic_synth.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) logic_synth $$c results/logic_synth.log
	if $(PYTEST) tests/test_sar_logic.py -k cells > results/test_sar_logic_cells.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) test_sar_logic_cells $$c results/test_sar_logic_cells.log
	$(RUN) fst2vcd -f build/icarus_sar_logic_test_sar_logic_COCOTB_TEST_FILTER/sar_logic.fst -o build/sar_gates.vcd > /dev/null
	if (cd logic && $(RUN) sta -no_init -exit power.tcl) > results/logic_power.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) logic_power $$c results/logic_power.log

decide: $(DECIDE)
	for f in $(DECIDE); do cp $$f results/decide_$$(basename $$(dirname $$f)).txt; done
	if ($(foreach v,$(VOLTS),$(PY) $(ROOT)/helpers/adc_results.py decide $(VOLT_$(v)) results/decide_*_$(v).txt &&) true) > results/decide.log 2>&1; then c=0; else c=$$?; fi
	$(SAVE) decide $$c results/decide.log results/decide_*.txt

offset: $(OFFSET)
	for f in $(OFFSET); do cp $$f results/offset_$$(basename $$(dirname $$f)).txt; done
	if $(PY) $(ROOT)/helpers/adc_results.py offset results/offset_*.txt > results/offset.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) offset $$c results/offset.log results/offset_*.txt

levels: $(LEVELS)
	for f in $(LEVELS); do cp $$f results/levels_$$(basename $$(dirname $$f)).txt; done
	if $(PY) $(ROOT)/helpers/adc_results.py levels results/levels_*.txt > results/levels.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) levels $$c results/levels.log results/levels_*.txt

convert: $(CONVERT)
	for f in $(CONVERT); do cp $$f results/convert_$$(basename $$(dirname $$f)).txt; done
	if for f in results/convert_*.txt; do $(PY) $(ROOT)/helpers/adc_results.py convert 1.2 $(K) $$f || exit 1; done > results/convert.log 2>&1; then c=0; else c=$$?; fi
	$(SAVE) convert $$c results/convert.log results/convert_*.txt

K := 5
N := 128

corner = printf '.lib cornerMOSlv.lib mos_%s\n.lib cornerCAP.lib cap_%s\n.temp %s\n.param vsupply=%s\n.param mm=%s\n' $(1) $(PASSIVE_$(1)) $(subst m,-,$(2)) $(VOLT_$(3)) $(4)

build/decide/%/decide.txt: tests/decide.cir $(COMPARATOR)
	mkdir -p $(@D)
	cp $^ $(@D)
	mv $(@D)/comparator.cir $(@D)/dut.cir
	$(call corner,$(word 1,$(subst _, ,$*)),$(word 2,$(subst _, ,$*)),$(word 3,$(subst _, ,$*)),0) > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b decide.cir > decide.log 2>&1

build/offset/%/offset.txt: tests/offset.cir $(COMPARATOR)
	mkdir -p $(@D)
	cp $^ $(@D)
	mv $(@D)/comparator.cir $(@D)/dut.cir
	printf '.lib cornerMOSlv.lib mos_tt_mismatch\n.temp 27\n.param vsupply=1.2\n.param mm=1\n.option seed=%s\n' $* > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b offset.cir > offset.log 2>&1

build/levels/mc%/dac_levels.txt: tests/dac_levels.cir $(DAC)
	mkdir -p $(@D)
	cp $^ $(@D)
	printf '.lib cornerMOSlv.lib mos_tt_mismatch\n.lib cornerCAP.lib cap_typ_mismatch\n.temp 27\n.param vsupply=1.2\n.param mm=1\n.option seed=%s\n' $* > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b dac_levels.cir > dac_levels.log 2>&1

build/levels/%/dac_levels.txt: tests/dac_levels.cir $(DAC)
	mkdir -p $(@D)
	cp $^ $(@D)
	$(call corner,$(word 1,$(subst _, ,$*)),$(word 2,$(subst _, ,$*)),$(word 3,$(subst _, ,$*)),0) > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b dac_levels.cir > dac_levels.log 2>&1

build/sar_logic.so: design/sar_logic.sv
	mkdir -p build/vlnggen
	cp $< build/vlnggen
	cd build/vlnggen && $(RUN) ngspice vlnggen sar_logic.sv > vlnggen.log 2>&1
	mv build/vlnggen/.so $@

build/convert/%/convert.txt: tests/convert.cir $(COMPARATOR) $(DAC) build/sar_logic.so
	mkdir -p $(@D)
	cp $^ $(@D)
	printf '.param n_samples=%s k_tone=%s\n' $(N) $(K) > $(@D)/tone.inc
	$(call corner,$(word 1,$(subst _, ,$*)),$(word 2,$(subst _, ,$*)),$(word 3,$(subst _, ,$*)),0) > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b convert.cir > convert.log 2>&1

broken: build/sar_logic.so
	mkdir -p results
	for p in broken/*.patch; do n=$$(basename $$p .patch); d=build/broken/$$n; mkdir -p $$d/build; cp -r design tests logic Makefile $$d; cp build/sar_logic.so $$d/build; \
	  patch -s -F0 -d $$d -p1 < $$p; want=$$(sed -n '1s/^Expected failure: //p' $$p); run=$$(sed -n '2s/^Run: //p' $$p); \
	  if $(MAKE) -C $$d $$run > $$d/make.log 2>&1; then c=1; elif [ -n "$$want" ] && grep -qF -- "$$want" $$d/results/$${run%% *}.log; then c=0; else c=2; fi; \
	  cp $$d/results/$${run%% *}.log results/broken_$$n.log; $(SAVE) broken_$$n $$c results/broken_$$n.log; done

.PHONY: all sar logic decide offset levels convert broken
.DELETE_ON_ERROR:
