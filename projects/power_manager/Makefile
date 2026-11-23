# power_manager commands: make speed | bitcell | ctrl | cosim | shifter | cmp_offset | windows | ref | unit | cpu_load | loop | loop_<corner> | model | model_check | gains | mem | gear_check | broken | all
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
BGL := $(ROOT)/projects/bandgap_ldo
CPU := $(ROOT)/projects/cpu
CMP_OFFSET := $(foreach n,$(shell seq 1 100),build/cmp_offset/$(n)/offset.txt)
LOOP := $(PY) $(ROOT)/helpers/dldo_loop.py
SPICE := $(ROOT)/helpers/ngspice.sh
LOGCHECK := $(PY) $(ROOT)/helpers/spice_log_check.py
CORNERS := tt_27_3v3 ss_125_3v0 ff_m40_3v6 sf_m40_3v6 fs_125_3v0
GAINS := $(shell sed -n 's/.*BIG = \([0-9]*\), P = \([0-9]*\), PB = \([0-9]*\).*/\1_\2_\3/p' tests/dldo_ctrl_cosim.sv)
HIGH := 8_8_8
GAIN_SET := 1_1_4 2_2_8 4_4_16 8_1_8 8_2_8 8_4_8 8_8_8 16_1_16 8_1_16 16_2_32
LOOP_FILES := tests/make_loop.py design/dldo_unit.cir design/dldo_sizes.inc design/shifter_hv.cir design/shifter_hv_sizes.inc design/comparator_sizes.inc design/tap_mux.cir $(ADC)/design/comparator.cir
corner = printf '.lib cornerMOSlv.lib mos_%s\n.lib cornerMOShv.lib mos_%s\n.lib cornerHBT.lib hbt_typ\n.lib cornerRES.lib res_typ\n.lib cornerCAP.lib cap_typ\n.temp %s\n.param vdd_v=1.2 vin_v=%s vsupply=%s mm=0\n' $(word 1,$(subst _, ,$(1))) $(word 1,$(subst _, ,$(1))) $(TEMP_$(word 2,$(subst _, ,$(1)))) $(subst v,.,$(word 3,$(subst _, ,$(1)))) $(subst v,.,$(word 3,$(subst _, ,$(1))))
part = $(word $(1),$(subst /, ,$(2)))

all: speed bitcell ctrl cosim shifter cmp_offset windows ref unit cpu_load loop model model_check gains mem gear_check broken

build/bitcell/%/read.txt: tests/bitcell_read.cir
	mkdir -p $(@D)
	cp $< $(@D)
	printf '.lib cornerMOSlv.lib mos_ss\n.temp %s\n' $(TEMP_$*) > $(@D)/corner.inc
	cd $(@D) && $(SPICE) bitcell_read.cir read.log

bitcell: build/bitcell/125/read.txt build/bitcell/m40/read.txt
	mkdir -p results
	cp build/bitcell/125/read.txt results/read_ss_125.txt; cp build/bitcell/m40/read.txt results/read_ss_m40.txt
	c=0; $(PY) $(ROOT)/helpers/speed_results.py bitcell results/read_ss_125.txt results/read_ss_m40.txt > results/bitcell.log 2>&1 || c=1; $(LOGCHECK) build/bitcell/*/read.log >> results/bitcell.log 2>&1 || c=1; $(SAVE) bitcell $$c results/bitcell.log results/read_ss_*.txt

build/so/%/dldo_ctrl.so: design/dldo_ctrl.sv tests/dldo_ctrl_cosim.sv
	mkdir -p $(@D)
	cp design/dldo_ctrl.sv $(@D)
	set -- $(subst _, ,$*); sed "s/BIG = [0-9]*, P = [0-9]*, PB = [0-9]*)/BIG = $$1, P = $$2, PB = $$3)/" tests/dldo_ctrl_cosim.sv > $(@D)/dldo_ctrl_cosim.sv; grep -q "BIG = $$1, P = $$2, PB = $$3)" $(@D)/dldo_ctrl_cosim.sv
	cd $(@D) && $(RUN) ngspice vlnggen dldo_ctrl_cosim.sv dldo_ctrl.sv > vlnggen.log 2>&1
	mv $(@D)/.so $@

cosim: build/so/$(GAINS)/dldo_ctrl.so tests/make_loop.py
	mkdir -p build/cosim results
	cp build/so/$(GAINS)/dldo_ctrl.so build/cosim
	cd build/cosim && $(RUN) python3 ../../tests/make_loop.py check && $(SPICE) cosim_check.cir cosim_check.log
	set -- $(subst _, ,$(GAINS)); c=0; $(PY) $(ROOT)/helpers/dldo_results.py cosim 128 $$1 $$2 $$3 build/cosim/check.txt > results/cosim.log 2>&1 || c=1; \
	  $(LOOP) coarse build/cosim/check.txt 128 9e-07 >> results/cosim.log 2>&1 || c=1; $(LOGCHECK) build/cosim/cosim_check.log >> results/cosim.log 2>&1 || c=1; $(SAVE) cosim $$c results/cosim.log

build/speed/%/speed.txt: tests/speed.cir
	mkdir -p $(@D)
	cp $< $(@D)
	printf '.lib cornerMOSlv.lib mos_%s\n.temp %s\n' $(word 1,$(subst _, ,$*)) $(TEMP_$(word 2,$(subst _, ,$*))) > $(@D)/corner.inc
	cd $(@D) && $(SPICE) speed.cir speed.log

speed: $(SPEED) tests/fo4.v tests/fo4.tcl
	mkdir -p build/fo4 results
	cp tests/fo4.v tests/fo4.tcl build/fo4
	for k in slow typ fast; do (cd build/fo4 && $(RUN) env CORNER=$$k sta -no_init -exit fo4.tcl) | tail -n 1 > results/fo4_$$k.txt; done
	for c in $(SPEED_CORNERS); do cp build/speed/$$c/speed.txt results/speed_$$c.txt; done
	c=0; $(PY) $(ROOT)/helpers/speed_results.py results/speed_*.txt results/fo4_*.txt > results/speed.log 2>&1 || c=1; $(LOGCHECK) $(SPEED:.txt=.log) >> results/speed.log 2>&1 || c=1; $(SAVE) speed $$c results/speed.log results/speed_*.txt results/fo4_*.txt

ctrl:
	mkdir -p results
	if $(PYTEST) tests/test_dldo_ctrl.py > results/test_dldo_ctrl.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) test_dldo_ctrl $$c results/test_dldo_ctrl.log

build/shifter/%/shifter.txt: tests/shifter.cir design/shifter_hv.cir design/shifter_hv_sizes.inc
	mkdir -p $(@D)
	cp $^ $(@D)
	set -- $(subst _, ,$*); printf '.lib cornerMOSlv.lib mos_%s\n.lib cornerMOShv.lib mos_%s\n.temp %s\n.param vdd_v=%s vin_v=%s\n' $$1 $$1 $(TEMP_$(word 2,$(subst _, ,$*))) $$(echo $$3 | tr v .) $$(echo $$4 | tr v .) > $(@D)/corner.inc
	cd $(@D) && $(SPICE) shifter.cir shifter.log

shifter: $(SHIFTER)
	mkdir -p results
	for c in $(SHIFTER_CORNERS); do cp build/shifter/$$c/shifter.txt results/shifter_$$c.txt; done
	c=0; $(PY) $(ROOT)/helpers/power_results.py shifter $(foreach c,$(SHIFTER_CORNERS),results/shifter_$(c).txt) > results/shifter.log 2>&1 || c=1; $(LOGCHECK) $(SHIFTER:.txt=.log) >> results/shifter.log 2>&1 || c=1; $(SAVE) shifter $$c results/shifter.log results/shifter_*.txt

build/cmp_offset/%/offset.txt: $(ADC)/tests/offset.cir $(ADC)/design/comparator.cir design/comparator_sizes.inc
	mkdir -p $(@D)
	cp $(ADC)/tests/offset.cir design/comparator_sizes.inc $(@D)
	cp $(ADC)/design/comparator.cir $(@D)/dut.cir
	printf '.lib cornerMOSlv.lib mos_tt_mismatch\n.temp 27\n.param vsupply=1.2\n.param mm=1\n.option seed=%s\n' $* > $(@D)/corner.inc
	cd $(@D) && $(SPICE) offset.cir offset.log

cmp_offset: $(CMP_OFFSET)
	mkdir -p results
	for n in $$(seq 1 100); do cp build/cmp_offset/$$n/offset.txt results/cmp_offset_$$n.txt; done
	c=0; $(PY) $(ROOT)/helpers/adc_results.py offset results/cmp_offset_*.txt > results/cmp_offset.log 2>&1 || c=1; $(LOGCHECK) $(CMP_OFFSET:.txt=.log) >> results/cmp_offset.log 2>&1 || c=1; $(SAVE) cmp_offset $$c results/cmp_offset.log results/cmp_offset_*.txt

windows: cmp_offset
	if $(LOOP) offsets 3e-3 results/cmp_offset_*.txt > results/windows.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) windows $$c results/windows.log results/cmp_offset_*.txt

build/ref/%/ref.txt: tests/make_loop.py design/dldo_sizes.inc $(BGL)/design/bandgap.cir $(BGL)/design/bandgap_sizes.inc $(BGL)/design/ldo.cir $(BGL)/design/ldo_sizes.inc
	mkdir -p $(@D)
	cp $(filter-out tests/make_loop.py,$^) $(@D)
	$(call corner,$*) > $(@D)/corner.inc
	cd $(@D) && $(RUN) python3 ../../../tests/make_loop.py ref && $(SPICE) ref.cir ref.log

ref: $(foreach c,$(CORNERS),build/ref/$(c)/ref.txt)
	mkdir -p results
	for c in $(CORNERS); do cp build/ref/$$c/ref.txt results/ref_$$c.txt; done
	c=0; $(LOOP) ref $^ > results/ref.log 2>&1 || c=1; $(LOGCHECK) $(^:.txt=.log) >> results/ref.log 2>&1 || c=1; $(SAVE) ref $$c results/ref.log results/ref_*.txt

build/unit/%/unit.inc: tests/make_loop.py design/dldo_unit.cir design/dldo_sizes.inc design/shifter_hv.cir design/shifter_hv_sizes.inc
	mkdir -p $(@D)
	cp $(filter-out tests/make_loop.py,$^) $(@D)
	$(call corner,$*) > $(@D)/corner.inc
	cd $(@D) && $(RUN) python3 ../../../tests/make_loop.py unit && $(SPICE) unit.cir unit.log
	$(LOOP) unit $(@D)/iv.txt $(@D)/delay.txt $@ 5e-08 > $(@D)/unit_inc.log 2>&1

unit: $(foreach c,$(CORNERS),build/unit/$(c)/unit.inc)
	mkdir -p results
	for c in $(CORNERS); do cp build/unit/$$c/delay.txt results/unit_delay_$$c.txt; cp build/unit/$$c/iv.txt results/unit_iv_$$c.txt; done
	cat $(foreach c,$(CORNERS),build/unit/$(c)/unit_inc.log) > results/unit.log
	c=0; $(LOGCHECK) $(foreach c,$(CORNERS),build/unit/$(c)/unit.log) >> results/unit.log 2>&1 || c=1; $(SAVE) unit $$c results/unit.log results/unit_delay_*.txt results/unit_iv_*.txt

build/cpu_load/cycles.txt: tests/cpu_load.tcl $(CPU)/build/cpu_gates.vcd $(CPU)/build/cpu_cells.v
	mkdir -p $(@D) results
	cd $(@D) && $(RUN) env CPU_CELLS=$(CPU)/build/cpu_cells.v CPU_VCD=$(CPU)/build/cpu_gates.vcd sta -no_init -exit $(CURDIR)/tests/cpu_load.tcl > sta.log 2>&1
	if $(LOOP) cpu_load $(@D)/sta.log $@ > results/cpu_load.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) cpu_load $$c results/cpu_load.log; exit $$c

cpu_load: build/cpu_load/cycles.txt

.SECONDEXPANSION:
build/run/%/loop.txt: $(LOOP_FILES) build/cpu_load/cycles.txt build/so/$$(call part,2,$$*)/dldo_ctrl.so build/ref/$$(call part,3,$$*)/ref.txt $$(if $$(findstring model,$$(call part,1,$$*)),build/unit/$$(call part,3,$$*)/unit.inc)
	mkdir -p $(@D)
	cp $(filter-out tests/make_loop.py,$(LOOP_FILES)) build/cpu_load/cycles.txt build/so/$(call part,2,$*)/dldo_ctrl.so build/ref/$(call part,3,$*)/ref.inc $(@D)
	$(if $(findstring model,$(call part,1,$*)),cp build/unit/$(call part,3,$*)/unit.inc $(@D))
	$(call corner,$(call part,3,$*)) > $(@D)/corner.inc
	cd $(@D) && $(RUN) python3 $(CURDIR)/tests/make_loop.py loop $(subst -, ,$(call part,1,$*)) && $(SPICE) loop.cir loop.log

loop_%: build/run/cpu/$(GAINS)/%/loop.txt
	mkdir -p results
	c=0; $(LOOP) loop $(<D)/schedule.txt $(<D)/ref.inc $< > results/loop_$*.log 2>&1 || c=1; $(LOGCHECK) $(<D)/loop.log >> results/loop_$*.log 2>&1 || c=1; $(SAVE) loop_$* $$c results/loop_$*.log

loop: $(foreach c,$(CORNERS),loop_$(c))

model: $(foreach c,$(CORNERS),build/run/cpu-model/$(GAINS)/$(c)/loop.txt)
	mkdir -p results
	c=0; for k in $(CORNERS); do d=build/run/cpu-model/$(GAINS)/$$k; echo "model at $$k, gains $(GAINS)"; $(LOOP) loop $$d/schedule.txt $$d/ref.inc $$d/loop.txt || c=1; $(LOGCHECK) $$d/loop.log || c=1; done > results/model.log 2>&1; $(SAVE) model $$c results/model.log

model_check: $(foreach c,$(CORNERS),build/run/cpu-model/$(GAINS)/$(c)/loop.txt build/run/cpu/$(GAINS)/$(c)/loop.txt) build/run/cpu-model/$(HIGH)/tt_27_3v3/loop.txt build/run/cpu/$(HIGH)/tt_27_3v3/loop.txt
	mkdir -p results
	c=0; for r in $(foreach c,$(CORNERS),$(GAINS)/$(c)) $(HIGH)/tt_27_3v3; do echo "model against transistors, gains and corner $$r (fitted on $(GAINS)/tt_27_3v3, validated on the others)"; \
	  $(LOOP) compare build/run/cpu/$$r/schedule.txt build/run/cpu/$$r/ref.inc build/run/cpu-model/$$r/loop.txt build/run/cpu/$$r/loop.txt || c=1; $(LOGCHECK) build/run/cpu-model/$$r/loop.log build/run/cpu/$$r/loop.log || c=1; done > results/model_check.log 2>&1; $(SAVE) model_check $$c results/model_check.log

gains: $(foreach g,$(GAIN_SET),build/run/cpu-model/$(g)/tt_27_3v3/loop.txt)
	mkdir -p results
	d=build/run/cpu-model/$(GAINS)/tt_27_3v3; c=0; $(LOOP) gains $$d/schedule.txt $$d/ref.inc $(foreach g,$(GAIN_SET),$(g) build/run/cpu-model/$(g)/tt_27_3v3/loop.txt) > results/gains.log 2>&1 || c=1; $(LOGCHECK) $(foreach g,$(GAIN_SET),build/run/cpu-model/$(g)/tt_27_3v3/loop.log) >> results/gains.log 2>&1 || c=1; $(SAVE) gains $$c results/gains.log

mem: build/run/mem/$(GAINS)/tt_27_3v3/loop.txt $(foreach c,$(CORNERS),build/run/mem-model/$(GAINS)/$(c)/loop.txt)
	mkdir -p results
	c=0; for r in mem/$(GAINS)/tt_27_3v3 $(foreach c,$(CORNERS),mem-model/$(GAINS)/$(c)); do d=build/run/$$r; echo "vdd_mem, $$r"; $(LOOP) loop $$d/schedule.txt $$d/ref.inc $$d/loop.txt || c=1; $(LOGCHECK) $$d/loop.log || c=1; done > results/mem.log 2>&1; \
	  d=build/run/mem/$(GAINS)/tt_27_3v3; echo "model against transistors, vdd_mem tt_27_3v3" >> results/mem.log; $(LOOP) compare $$d/schedule.txt $$d/ref.inc build/run/mem-model/$(GAINS)/tt_27_3v3/loop.txt $$d/loop.txt >> results/mem.log 2>&1 || c=1; $(SAVE) mem $$c results/mem.log

gear_check: build/run/short/$(GAINS)/tt_27_3v3/loop.txt build/run/short-trap/$(GAINS)/tt_27_3v3/loop.txt
	mkdir -p results
	d=build/run/short/$(GAINS)/tt_27_3v3; c=0; $(LOOP) compare $$d/schedule.txt $$d/ref.inc build/run/short-trap/$(GAINS)/tt_27_3v3/loop.txt $$d/loop.txt > results/gear_check.log 2>&1 || c=1; $(LOGCHECK) $$d/loop.log build/run/short-trap/$(GAINS)/tt_27_3v3/loop.log >> results/gear_check.log 2>&1 || c=1; $(SAVE) gear_check $$c results/gear_check.log

broken:
	rm -rf build/broken
	mkdir -p results build/broken
	e=0; for p in broken/dldo_*.patch; do n=$$(basename $$p .patch); d=build/broken/$$n; mkdir -p $$d/build; cp -rp design tests Makefile uses.txt $$d; \
	  for b in cpu_load ref unit; do if [ -d build/$$b ]; then cp -rp build/$$b $$d/build; fi; done; \
	  patch -s -F0 -d $$d -p1 < $$p; want=$$(sed -n '1s/^Expected failure: //p' $$p); run=$$(sed -n '2s/^Run: //p' $$p); log=$$(sed -n '3s/^Log: //p' $$p); \
	  if $(MAKE) -C $$d $$run > $$d/make.log 2>&1; then c=1; elif [ -n "$$want" ] && grep -qF -- "$$want" $$d/$$log; then c=0; else c=2; fi; \
	  cp $$d/$$log results/broken_$$n.log; $(SAVE) broken_$$n $$c results/broken_$$n.log || e=1; done; exit $$e

.PHONY: all speed bitcell ctrl cosim shifter cmp_offset windows ref unit cpu_load loop model model_check gains mem gear_check broken

-include supervisor.mk
-include cells.mk
