# power_manager commands: make speed | ctrl | shifter | cmp_offset | all
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
ROOT := $(shell git rev-parse --show-toplevel)
RUN := $(ROOT)/setup/run.sh
PY := $(RUN) env PYTHONPATH=$(ROOT)/helpers python3
SAVE := $(RUN) python3 $(ROOT)/helpers/save_result.py results/summary.json
SPEED_CORNERS := tt_25 ss_125 ss_m40 ff_m40 ff_125
SPEED := $(foreach c,$(SPEED_CORNERS),build/speed/$(c)/speed.txt)
TEMP_25 := 25
TEMP_125 := 125
TEMP_m40 := -40
TEMP_27 := 27
PYTEST := $(RUN) env PYTHONPATH=$(ROOT)/helpers python3 -m pytest -q -s -p no:cacheprovider
SHIFTER_CORNERS := tt_27_1v2_3v3 $(foreach p,ss ff sf fs,$(foreach t,m40 125,$(foreach v,1v08_3v6 1v32_3v0,$(p)_$(t)_$(v))))
SHIFTER := $(foreach c,$(SHIFTER_CORNERS),build/shifter/$(c)/shifter.txt)
ADC := $(ROOT)/projects/adc
CMP_OFFSET := $(foreach n,$(shell seq 1 100),build/cmp_offset/$(n)/offset.txt)

all: speed ctrl shifter cmp_offset

build/speed/%/speed.txt: tests/speed.cir
	mkdir -p $(@D)
	cp $< $(@D)
	printf '.lib cornerMOSlv.lib mos_%s\n.temp %s\n' $(word 1,$(subst _, ,$*)) $(TEMP_$(word 2,$(subst _, ,$*))) > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b speed.cir > speed.log 2>&1

speed: $(SPEED) tests/fo4.v tests/fo4.tcl
	mkdir -p build/fo4 results
	cp tests/fo4.v tests/fo4.tcl build/fo4
	for k in slow typ fast; do (cd build/fo4 && $(RUN) env CORNER=$$k sta -no_init -exit fo4.tcl) | tail -n 1 > results/fo4_$$k.txt; done
	for c in $(SPEED_CORNERS); do cp build/speed/$$c/speed.txt results/speed_$$c.txt; done
	if $(PY) $(ROOT)/helpers/speed_results.py results/speed_*.txt results/fo4_*.txt > results/speed.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) speed $$c results/speed.log results/speed_*.txt results/fo4_*.txt

ctrl:
	mkdir -p results
	if $(PYTEST) tests/test_dldo_ctrl.py > results/test_dldo_ctrl.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) test_dldo_ctrl $$c results/test_dldo_ctrl.log

build/shifter/%/shifter.txt: tests/shifter.cir design/shifter_hv.cir design/shifter_hv_sizes.inc
	mkdir -p $(@D)
	cp $^ $(@D)
	set -- $(subst _, ,$*); printf '.lib cornerMOSlv.lib mos_%s\n.lib cornerMOShv.lib mos_%s\n.temp %s\n.param vdd_v=%s vin_v=%s\n' $$1 $$1 $(TEMP_$(word 2,$(subst _, ,$*))) $$(echo $$3 | tr v .) $$(echo $$4 | tr v .) > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b shifter.cir > shifter.log 2>&1

shifter: $(SHIFTER)
	mkdir -p results
	for c in $(SHIFTER_CORNERS); do cp build/shifter/$$c/shifter.txt results/shifter_$$c.txt; done
	if $(PY) $(ROOT)/helpers/power_results.py shifter $(foreach c,$(SHIFTER_CORNERS),results/shifter_$(c).txt) > results/shifter.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) shifter $$c results/shifter.log results/shifter_*.txt

build/cmp_offset/%/offset.txt: $(ADC)/tests/offset.cir $(ADC)/design/comparator.cir design/comparator_sizes.inc
	mkdir -p $(@D)
	cp $(ADC)/tests/offset.cir design/comparator_sizes.inc $(@D)
	cp $(ADC)/design/comparator.cir $(@D)/dut.cir
	printf '.lib cornerMOSlv.lib mos_tt_mismatch\n.temp 27\n.param vsupply=1.2\n.param mm=1\n.option seed=%s\n' $* > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b offset.cir > offset.log 2>&1

cmp_offset: $(CMP_OFFSET)
	mkdir -p results
	for n in $$(seq 1 100); do cp build/cmp_offset/$$n/offset.txt results/cmp_offset_$$n.txt; done
	if $(PY) $(ROOT)/helpers/adc_results.py offset results/cmp_offset_*.txt > results/cmp_offset.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) cmp_offset $$c results/cmp_offset.log results/cmp_offset_*.txt

.PHONY: all speed ctrl shifter cmp_offset
