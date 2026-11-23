# adc commands: make sar | logic | decide | offset | levels | trim | uic_check | convert | supply_corners | ramp | supplied | refs | supply_wave | shunt_check | gear_check | ktc | model | supply_current | fom | broken | review | layout | post_layout | all
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
ROOT := $(shell git rev-parse --show-toplevel)
RUN := $(ROOT)/setup/run.sh
PY := $(RUN) env PYTHONPATH=$(ROOT)/helpers python3
PYTEST := $(RUN) env PYTHONPATH=$(ROOT)/helpers python3 -m pytest -q -s -p no:cacheprovider
SAVE := $(RUN) python3 $(ROOT)/helpers/save_result.py results/summary.json
LOGS := $(PY) $(ROOT)/helpers/spice_log_check.py
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
TRIM_CORNERS := $(foreach p,$(PROCESS),$(p)_27_nom) tt_m40_nom tt_125_nom tt_27_min tt_27_hi
TRIM := $(foreach c,$(TRIM_CORNERS),build/trim/$(c)/trim_levels.txt) $(foreach n,$(shell seq 1 20),build/trim/mc$(n)/trim_levels.txt)
CONVERT_CORNERS := $(foreach p,$(PROCESS),$(foreach t,$(TEMPS),$(p)_$(t)_nom))
CONVERT := $(foreach c,$(CONVERT_CORNERS),build/convert/$(c)/convert.txt)
SUPPLY_CORNERS := tt_27_min tt_27_hi ss_125_min ff_m40_hi
SUPPLY := $(foreach c,$(SUPPLY_CORNERS),build/convert/$(c)/convert.txt)
COMPARATOR := design/comparator.cir design/comparator_sizes.inc
DAC := design/cap_dac.cir design/cap_dac_sizes.inc
BANDGAP_LDO := $(foreach f,bandgap.cir bandgap_sizes.inc ldo.cir ldo_sizes.inc,$(ROOT)/projects/bandgap_ldo/design/$(f))
TRIMS := $(ROOT)/projects/bandgap_ldo/results/corners.log
SIM_SDF := $(ROOT)/projects/fifo_bridge/timing/sim_sdf.py
SUPPLIED_CORNERS := tt_27 ss_125 ff_m40
SUPPLIED := $(foreach c,$(SUPPLIED_CORNERS),build/supplied/$(c)/convert.txt)
LAYOUT_CORNERS := tt_27_nom ss_125_nom ff_m40_nom
POST := $(foreach c,$(LAYOUT_CORNERS),build/post_layout/$(c)/convert.txt)
CORNERS_LOGIC := slow typ fast
K := 5
N := 128

all: sar logic decide offset levels trim uic_check convert supply_corners ramp supplied refs supply_wave shunt_check gear_check ktc model supply_current fom broken review layout post_layout

sar:
	mkdir -p results
	if $(PYTEST) tests/test_sar_logic.py -k "not gates" > results/test_sar_logic.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) test_sar_logic $$c results/test_sar_logic.log

logic:
	mkdir -p build results
	$(RUN) bash -c 'l=$$PDK_ROOT/$$PDK/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell; cp $${l}_slow_1p08V_125C.lib build/slow.lib; cp $${l}_typ_1p20V_25C.lib build/typ.lib; cp $${l}_fast_1p32V_m40C.lib build/fast.lib'
	if (cd logic && $(RUN) yosys -s synth.ys) > results/logic_synth.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) logic_synth $$c results/logic_synth.log
	for k in $(CORNERS_LOGIC); do \
	  if (cd logic && $(RUN) env CORNER=$$k sta -no_init -exit timing.tcl) > results/logic_timing_$$k.log 2>&1; then c=0; else c=$$?; fi; \
	  python3 $(SIM_SDF) build/sar_logic_$$k.sdf build/sar_logic_$${k}_sim.sdf; $(SAVE) logic_timing_$$k $$c results/logic_timing_$$k.log; done
	if $(PYTEST) tests/test_sar_logic.py -k gates > results/test_sar_logic_gates.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) test_sar_logic_gates $$c results/test_sar_logic_gates.log
	for k in $(CORNERS_LOGIC); do d=$$(ls -d build/icarus_sar_logic_test_sar_logic_*$${k^^}*); \
	  $(RUN) fst2vcd -f $$d/sar_logic.fst -o build/gates_$$k.vcd > /dev/null; \
	  if (cd logic && $(RUN) env CORNER=$$k VCD=../build/gates_$$k.vcd sta -no_init -exit power.tcl) > results/logic_power_$$k.log 2>&1; then c=0; else c=$$?; fi; \
	  $(SAVE) logic_power_$$k $$c results/logic_power_$$k.log; done

decide: $(DECIDE)
	for f in $(DECIDE); do cp $$f results/decide_$$(basename $$(dirname $$f)).txt; done
	if { $(LOGS) $(DECIDE:.txt=.log) && $(foreach v,$(VOLTS),$(PY) $(ROOT)/helpers/adc_results.py decide $(VOLT_$(v)) results/decide_*_$(v).txt &&) true; } > results/decide.log 2>&1; then c=0; else c=$$?; fi; \
	$(SAVE) decide $$c results/decide.log results/decide_*.txt

offset: $(OFFSET)
	for f in $(OFFSET); do cp $$f results/offset_$$(basename $$(dirname $$f)).txt; done
	if { $(LOGS) $(OFFSET:.txt=.log) && $(PY) $(ROOT)/helpers/adc_results.py offset results/offset_*.txt; } > results/offset.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) offset $$c results/offset.log results/offset_*.txt

levels: $(LEVELS)
	for f in $(LEVELS); do cp $$f results/levels_$$(basename $$(dirname $$f)).txt; done
	if { $(LOGS) $(patsubst %/dac_levels.txt,%/dac_levels.log,$(LEVELS)) && $(PY) $(ROOT)/helpers/adc_results.py levels results/levels_*.txt; } > results/levels.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) levels $$c results/levels.log results/levels_*.txt

trim: $(TRIM)
	for f in $(TRIM); do cp $$f results/trim_$$(basename $$(dirname $$f)).txt; done
	if { $(LOGS) $(patsubst %/trim_levels.txt,%/trim_levels.log,$(TRIM)) && $(PY) $(ROOT)/helpers/adc_trim.py levels results/trim_*.txt; } > results/trim.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) trim $$c results/trim.log results/trim_*.txt

convert: $(CONVERT)
	for f in $(CONVERT); do c=$$(basename $$(dirname $$f)); cp $$f results/convert_$$c.txt; cp $$(dirname $$f)/measure.txt results/measure_$$c.txt; done
	if { $(LOGS) $(CONVERT:.txt=.log) && $(PY) $(ROOT)/helpers/adc_trim.py code 1.2 $(CONVERT) && for c in $(CONVERT_CORNERS); do $(PY) $(ROOT)/helpers/adc_results.py convert 1.2 $(N) results/convert_$$c.txt results/measure_$$c.txt || exit 1; done; } > results/convert.log 2>&1; then c=0; else c=$$?; fi; \
	$(SAVE) convert $$c results/convert.log results/convert_*_nom.txt results/measure_*_nom.txt

supply_corners: $(SUPPLY)
	for f in $(SUPPLY); do c=$$(basename $$(dirname $$f)); cp $$f results/convert_$$c.txt; cp $$(dirname $$f)/measure.txt results/measure_$$c.txt; done
	if { $(LOGS) $(SUPPLY:.txt=.log) && for c in $(SUPPLY_CORNERS); do v=$$(case $$c in *_min) echo $(VOLT_min);; *_hi) echo $(VOLT_hi);; esac); \
	  $(PY) $(ROOT)/helpers/adc_trim.py code $$v build/convert/$$c/convert.txt && $(PY) $(ROOT)/helpers/adc_results.py convert $$v $(N) results/convert_$$c.txt results/measure_$$c.txt || exit 1; done; } > results/supply_corners.log 2>&1; then c=0; else c=$$?; fi; \
	$(SAVE) supply_corners $$c results/supply_corners.log $(foreach c,$(SUPPLY_CORNERS),results/convert_$(c).txt results/measure_$(c).txt)

corner = printf '.lib cornerMOSlv.lib mos_%s\n.lib cornerCAP.lib cap_%s\n.temp %s\n.param vsupply=%s\n.param mm=%s\n' $(1) $(PASSIVE_$(1)) $(subst m,-,$(2)) $(VOLT_$(3)) $(4)
mismatch = printf '.lib cornerMOSlv.lib mos_tt_mismatch\n.lib cornerCAP.lib cap_typ_mismatch\n.temp 27\n.param vsupply=1.2\n.param mm=1\n.option seed=%s\n' $(1)
words = $(word 1,$(subst _, ,$(1))),$(word 2,$(subst _, ,$(1))),$(word 3,$(subst _, ,$(1)))

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
	$(call mismatch,$*) > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b dac_levels.cir > dac_levels.log 2>&1

build/levels/%/dac_levels.txt: tests/dac_levels.cir $(DAC)
	mkdir -p $(@D)
	cp $^ $(@D)
	$(call corner,$(word 1,$(subst _, ,$*)),$(word 2,$(subst _, ,$*)),$(word 3,$(subst _, ,$*)),0) > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b dac_levels.cir > dac_levels.log 2>&1

build/trim/mc%/trim_levels.txt: tests/trim_levels.cir $(DAC)
	mkdir -p $(@D)
	cp $^ $(@D)
	$(call mismatch,$*) > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b trim_levels.cir > trim_levels.log 2>&1

build/trim/%/trim_levels.txt: tests/trim_levels.cir $(DAC)
	mkdir -p $(@D)
	cp $^ $(@D)
	$(call corner,$(word 1,$(subst _, ,$*)),$(word 2,$(subst _, ,$*)),$(word 3,$(subst _, ,$*)),0) > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b trim_levels.cir > trim_levels.log 2>&1

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

build/ramp/%/ramp.txt: tests/ramp.cir $(COMPARATOR) $(DAC) build/sar_logic.so $(ROOT)/helpers/adc_ramp.py
	mkdir -p $(@D)
	cp $(filter-out %.py,$^) $(@D)
	$(PY) $(ROOT)/helpers/adc_ramp.py pwl $(@D)/ramp.inc
	$(call corner,$(word 1,$(subst _, ,$*)),$(word 2,$(subst _, ,$*)),$(word 3,$(subst _, ,$*)),0) > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b ramp.cir > ramp.log 2>&1

ramp: build/ramp/tt_27_nom/ramp.txt
	mkdir -p results
	cp $< results/ramp_tt_27_nom.txt
	if { $(LOGS) build/ramp/tt_27_nom/ramp.log && $(PY) $(ROOT)/helpers/adc_trim.py code 1.2 $< && $(PY) $(ROOT)/helpers/adc_ramp.py transitions 1.2 results/ramp_tt_27_nom.txt; } > results/ramp.log 2>&1; then c=0; else c=$$?; fi; \
	$(SAVE) ramp $$c results/ramp.log results/ramp_tt_27_nom.txt

build/supplied/%/convert.txt: tests/supplied.cir $(COMPARATOR) $(DAC) design/reference.cir design/reference_sizes.inc $(BANDGAP_LDO) $(TRIMS) build/sar_logic.so
	mkdir -p $(@D)
	cp $(filter-out $(TRIMS),$^) $(@D)
	printf '.param n_samples=%s k_tone=%s\n' $(N) $(K) > $(@D)/tone.inc
	p=$$(echo $* | cut -d_ -f1); t=$$(echo $* | cut -d_ -f2 | tr m -); q=$(PASSIVE_$(word 1,$(subst _, ,$*))); \
	  code=$$(sed -n "s/^dc_$${p}_3v3 .* code=\([0-9]*\) .*/\1/p" $(TRIMS)); [ -n "$$code" ]; \
	  printf '.lib cornerMOSlv.lib mos_%s\n.lib cornerMOShv.lib mos_%s\n.lib cornerHBT.lib hbt_%s\n.lib cornerRES.lib res_%s\n.lib cornerCAP.lib cap_%s\n.temp %s\n.param vsupply=1.2 vsupply33=3.3 mm=0\n.param trim3=%s trim2=%s trim1=%s trim0=%s\n' \
	  $$p $$p $$q $$q $$q $$t $$((code / 8)) $$((code / 4 % 2)) $$((code / 2 % 2)) $$((code % 2)) > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b supplied.cir > supplied.log 2>&1

supplied: $(SUPPLIED) $(foreach c,$(SUPPLIED_CORNERS),build/convert/$(c)_nom/convert.txt)
	mkdir -p results
	for c in $(SUPPLIED_CORNERS); do cp build/supplied/$$c/convert.txt results/supplied_$$c.txt; cp build/supplied/$$c/measure.txt results/supplied_measure_$$c.txt; done
	if { $(LOGS) $(SUPPLIED:convert.txt=supplied.log) && for c in $(SUPPLIED_CORNERS); do \
	  $(PY) $(ROOT)/helpers/adc_results.py supplied 1.2 $(N) results/supplied_$$c.txt results/supplied_measure_$$c.txt build/convert/$${c}_nom/convert.txt build/convert/$${c}_nom/measure.txt || exit 1; done; } > results/supplied.log 2>&1; then c=0; else c=$$?; fi; \
	  $(SAVE) supplied $$c results/supplied.log results/supplied_*.txt

build/refs/%/convert.txt: build/supplied/%/convert.txt
	mkdir -p $(@D)
	cp build/supplied/$*/*.cir build/supplied/$*/*.inc build/sar_logic.so $(@D)
	sed -i 's/^.option interp rshunt=1e13 method=gear$$/.option rshunt=1e13 method=gear/; s/^.tran 50n .*/.tran 50n 20u/; /^let span/,/^echo/d; s/^wrdata convert.txt .*/wrdata convert.txt v(cclk) v(vref_hi) v(vcm) v(vref_lo)/' $(@D)/supplied.cir
	grep -q '^wrdata convert.txt v(cclk)' $(@D)/supplied.cir
	cd $(@D) && $(RUN) ngspice -b supplied.cir > supplied.log 2>&1

REFS := $(foreach c,$(SUPPLIED_CORNERS),build/refs/$(c)/convert.txt)

refs: $(REFS)
	mkdir -p results
	for c in $(SUPPLIED_CORNERS); do cp build/refs/$$c/convert.txt results/refs_$$c.txt; done
	if { $(LOGS) $(REFS:convert.txt=supplied.log) && $(PY) $(ROOT)/helpers/adc_supply.py refs 1.2 $(foreach c,$(SUPPLIED_CORNERS),results/refs_$(c).txt); } > results/refs.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) refs $$c results/refs.log results/refs_*.txt

build/supply_wave/%/wave.txt: tests/convert.cir $(COMPARATOR) $(DAC) build/sar_logic.so
	mkdir -p $(@D)
	cp $^ $(@D)
	printf '.param n_samples=%s k_tone=%s\n' $(N) $(K) > $(@D)/tone.inc
	$(call corner,$(word 1,$(subst _, ,$*)),$(word 2,$(subst _, ,$*)),$(word 3,$(subst _, ,$*)),0) > $(@D)/corner.inc
	sed -i 's/^.option interp rshunt=1e13 method=gear$$/.option rshunt=1e13 method=gear/; s/^.tran 50n .*/.tran 50n 14u/; /^let span/,/^echo/d; s/^wrdata convert.txt .*/let isup = -i(VDD)\nwrdata wave.txt isup/' $(@D)/convert.cir
	grep -q '^wrdata wave.txt isup' $(@D)/convert.cir
	cd $(@D) && $(RUN) ngspice -b convert.cir > convert.log 2>&1

WAVE_CORNERS := tt_27_nom ff_m40_hi
WAVE := $(foreach c,$(WAVE_CORNERS),build/supply_wave/$(c)/wave.txt)

supply_wave: $(WAVE)
	mkdir -p results
	for c in $(WAVE_CORNERS); do cp build/supply_wave/$$c/wave.txt results/supply_wave_$$c.txt; done
	if { $(LOGS) $(WAVE:wave.txt=convert.log) && $(PY) $(ROOT)/helpers/adc_supply.py wave 14e-6 $(foreach c,$(WAVE_CORNERS),results/supply_wave_$(c).txt); } > results/supply_wave.log 2>&1; then c=0; else c=$$?; fi; \
	$(SAVE) supply_wave $$c results/supply_wave.log results/supply_wave_*.txt

uic_check: tests/dac_levels.cir $(DAC)
	mkdir -p results
	for s in op uic; do d=build/uic_check/$$s; mkdir -p $$d; cp $(DAC) $$d; sed '/^.option reltol=1e-5 vntol=1e-8$$/d' tests/dac_levels.cir > $$d/dac_levels.cir; \
	  $(call corner,ff,27,nom,0) > $$d/corner.inc; done
	sed -i 's/ uic$$//' build/uic_check/op/dac_levels.cir
	for s in op uic; do (cd build/uic_check/$$s && $(RUN) ngspice -b dac_levels.cir > dac_levels.log 2>&1); cp build/uic_check/$$s/dac_levels.txt results/uic_check_$$s.txt; done
	if { $(LOGS) build/uic_check/op/dac_levels.log build/uic_check/uic/dac_levels.log && $(PY) $(ROOT)/helpers/adc_results.py same results/uic_check_op.txt results/uic_check_uic.txt; } > results/uic_check.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) uic_check $$c results/uic_check.log results/uic_check_*.txt

build/shunt_check/%/convert.txt: build/convert/%/convert.txt
	mkdir -p $(@D)
	cp build/convert/$*/*.cir build/convert/$*/*.inc build/sar_logic.so $(@D)
	if [ $* = tt_27_nom ]; then o='.option interp method=gear'; else o='.option interp rshunt=1e14 method=gear'; fi; \
	  sed -i "s/^.option interp rshunt=1e13 method=gear$$/$$o/" $(@D)/convert.cir; ! grep -q 'rshunt=1e13' $(@D)/convert.cir
	cd $(@D) && $(RUN) ngspice -b convert.cir > convert.log 2>&1

shunt_check: build/shunt_check/tt_27_nom/convert.txt build/shunt_check/tt_m40_nom/convert.txt
	mkdir -p results
	for c in tt_27_nom tt_m40_nom; do cp build/convert/$$c/convert.txt results/shunt_check_with_$$c.txt; cp build/shunt_check/$$c/convert.txt results/shunt_check_changed_$$c.txt; done
	if { $(LOGS) $(^:.txt=.log) && for c in tt_27_nom tt_m40_nom; do $(PY) $(ROOT)/helpers/adc_results.py same_codes 1.2 results/shunt_check_with_$$c.txt results/shunt_check_changed_$$c.txt || exit 1; done; } > results/shunt_check.log 2>&1; then c=0; else c=$$?; fi; \
	$(SAVE) shunt_check $$c results/shunt_check.log results/shunt_check_*.txt

build/gear_check/%/convert.txt: tests/convert.cir $(COMPARATOR) $(DAC) build/sar_logic.so
	mkdir -p $(@D)
	cp $^ $(@D)
	printf '.param n_samples=%s k_tone=%s\n' $(N) $(K) > $(@D)/tone.inc
	c=$$(echo $* | cut -d_ -f1-3); m=$$(echo $* | cut -d_ -f4); printf '.lib cornerMOSlv.lib mos_tt\n.lib cornerCAP.lib cap_typ\n.temp %s\n.param vsupply=1.2\n.param mm=0\n' $$(echo $$c | cut -d_ -f2 | tr m -) > $(@D)/corner.inc; \
	  if [ $$m = gear ]; then o='.option rshunt=1e13 method=gear'; else o='.option rshunt=1e13'; fi; \
	  sed -i "s/^.option interp rshunt=1e13 method=gear$$/$$o/; s/^.tran 50n .*/.tran 50n 30u/; /^let span/,/^echo/d; s/^wrdata convert.txt .*/wrdata convert.txt v(cclk) v(top) v(vcm)/" $(@D)/convert.cir
	cd $(@D) && $(RUN) ngspice -b convert.cir > convert.log 2>&1

build/gear_check/decide/decide.txt: build/decide/tt_27_nom/decide.txt
	mkdir -p $(@D)
	cp build/decide/tt_27_nom/*.cir build/decide/tt_27_nom/*.inc $(@D)
	sed -i 's/^.option reltol=1e-5 vntol=1e-8$$/.option reltol=1e-5 vntol=1e-8 method=gear/' $(@D)/decide.cir
	cd $(@D) && $(RUN) ngspice -b decide.cir > decide.log 2>&1

GEAR := $(foreach c,tt_27_nom tt_m40_nom tt_125_nom,$(foreach m,gear trapezoidal,build/gear_check/$(c)_$(m)/convert.txt))

gear_check: $(GEAR) build/gear_check/decide/decide.txt
	mkdir -p results
	for c in tt_27_nom tt_m40_nom tt_125_nom; do for m in gear trapezoidal; do cp build/gear_check/$${c}_$$m/convert.txt results/gear_check_$${m}_$$c.txt; done; done
	cp build/gear_check/decide/decide.txt results/gear_check_decide_gear.txt; cp build/decide/tt_27_nom/decide.txt results/gear_check_decide_trapezoidal.txt
	if { $(LOGS) $(GEAR:.txt=.log) build/gear_check/decide/decide.log && for c in tt_27_nom tt_m40_nom tt_125_nom; do $(PY) $(ROOT)/helpers/adc_results.py top 1.2 results/gear_check_gear_$$c.txt results/gear_check_trapezoidal_$$c.txt || exit 1; done && \
	  $(PY) $(ROOT)/helpers/adc_results.py decide_methods results/gear_check_decide_trapezoidal.txt results/gear_check_decide_gear.txt; } > results/gear_check.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) gear_check $$c results/gear_check.log results/gear_check_*.txt

build/ktc/ktc.txt: tests/ktc.cir $(DAC)
	mkdir -p $(@D)
	cp $^ $(@D)
	$(call corner,tt,27,nom,0) > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b ktc.cir > ktc.log 2>&1

ktc: build/ktc/ktc.txt
	mkdir -p results
	cp $< results/ktc_tt_27_nom.txt
	if { $(LOGS) build/ktc/ktc.log && $(PY) $(ROOT)/helpers/adc_supply.py ktc results/ktc_tt_27_nom.txt; } > results/ktc.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) ktc $$c results/ktc.log results/ktc_tt_27_nom.txt

build/model/adc_model: design/adc_model.sv design/sar_logic.sv tests/model_tb.sv
	mkdir -p $(@D)
	cd $(@D) && $(RUN) verilator --binary -j 1 -Wno-fatal --top-module model_tb -o adc_model ../../design/adc_model.sv ../../design/sar_logic.sv ../../tests/model_tb.sv > build.log 2>&1
	cp $(@D)/obj_dir/adc_model $@

model: build/model/adc_model trim levels ramp convert supply_corners offset
	mkdir -p results
	if $(PY) $(ROOT)/helpers/adc_model.py all build/model/adc_model build/model results > results/model.log 2>&1; then c=0; else c=$$?; fi; \
	$(SAVE) model $$c results/model.log results/model_*.txt

supply_current: convert
	mkdir -p results
	if $(PY) $(ROOT)/helpers/adc_supply.py current 1.2 results/convert_tt_27_nom.txt results/measure_tt_27_nom.txt > results/supply_current.log 2>&1; then c=0; else c=$$?; fi; \
	$(SAVE) supply_current $$c results/supply_current.log results/convert_tt_27_nom.txt results/measure_tt_27_nom.txt

fom: convert logic
	mkdir -p results
	if $(PY) $(ROOT)/helpers/adc_supply.py fom 1.2 $(N) results/convert_tt_27_nom.txt results/measure_tt_27_nom.txt results/logic_power_typ.log > results/fom.log 2>&1; then c=0; else c=$$?; fi; \
	$(SAVE) fom $$c results/fom.log results/convert_tt_27_nom.txt results/measure_tt_27_nom.txt results/logic_power_typ.log

broken: build/sar_logic.so
	mkdir -p results
	for p in broken/*.patch; do n=$$(basename $$p .patch); d=build/broken/$$n; rm -rf $$d; mkdir -p $$d/build; cp -r design tests logic Makefile $$d; cp build/sar_logic.so $$d/build; \
	  patch -s -F0 -d $$d -p1 < $$p; want=$$(sed -n '1s/^Expected failure: //p' $$p); pass=$$(sed -n '1s/^Expected pass: //p' $$p); run=$$(sed -n '2s/^Run: //p' $$p); \
	  if $(MAKE) -C $$d $$run > $$d/make.log 2>&1; then ok=0; else ok=1; fi; \
	  cp $$d/results/$${run%% *}.log results/broken_$$n.log; \
	  if [ -n "$$pass" ]; then c=$$ok; elif [ $$ok = 1 ] && [ -n "$$want" ] && grep -qF -- "$$want" results/broken_$$n.log && ! grep -q ': FAIL$$' results/broken_$$n.log; then c=0; else c=1; fi; \
	  $(SAVE) broken_$$n $$c results/broken_$$n.log; done

review: build/sar_logic.so
	mkdir -p results
	for p in review/*.patch; do n=$$(basename $$p .patch); d=build/review/$$n; rm -rf $$d; mkdir -p $$d/build; cp -r design tests logic Makefile $$d; cp build/sar_logic.so $$d/build; \
	  patch -s -F0 -d $$d -p1 < $$p; run=$$(sed -n '2s/^Run: //p' $$p); log=$$d/results/$${run%% *}.log; \
	  if $(MAKE) -C $$d $$run > $$d/make.log 2>&1; then ok=0; else ok=$$?; fi; \
	  { sed -n 1p $$p; echo "make $$run exit $$ok"; cat $$log; } > results/review_$$n.log; \
	  if [ -s $$log ]; then c=0; else c=1; fi; $(SAVE) review_$$n $$c results/review_$$n.log; done

build/layout/adc_core.cdl: layout/core.cir $(COMPARATOR) $(DAC) $(ROOT)/helpers/spice_flatten.py
	mkdir -p build/layout
	cat design/cap_dac_sizes.inc design/comparator_sizes.inc > build/layout/sizes.inc
	python3 $(ROOT)/helpers/spice_flatten.py adc_core build/layout/sizes.inc design/cap_dac.cir design/comparator.cir layout/core.cir > $@

build/layout/adc_core.gds: build/layout/adc_core.cdl layout/adc_core.py $(ROOT)/helpers/row_layout.py
	$(RUN) env NETLIST=build/layout/adc_core.cdl OUT=build/layout klayout -b -r layout/adc_core.py > build/layout/generate.log 2>&1

layout: build/layout/adc_core.gds
	mkdir -p results
	rm -rf build/layout/drc build/layout/lvs
	cd build/layout && if $(RUN) bash -c 'python3 $$PDK_ROOT/$$PDK/libs.tech/klayout/tech/drc/run_drc.py --path=adc_core.gds --topcell=adc_core --run_dir=drc --no_density' > drc.log 2>&1; then e=0; else e=$$?; fi; echo "run_drc exit $$e" >> drc.log
	cd build/layout && if $(RUN) bash -c 'python3 $$PDK_ROOT/$$PDK/libs.tech/klayout/tech/lvs/run_lvs.py --layout=adc_core.gds --netlist=adc_core.cdl --topcell=adc_core --run_dir=lvs --combine_devices --disable_tap_extraction' > lvs.log 2>&1; then e=0; else e=$$?; fi; echo "run_lvs exit $$e" >> lvs.log
	cd build/layout && if $(RUN) klayout -b -rd path=lvs/adc_core.lvsdb -r $(ROOT)/helpers/lvs_names.py >> lvs.log 2>&1; then e=0; else e=$$?; fi; echo "lvs_names exit $$e" >> lvs.log
	cp build/layout/drc.log results/layout_drc.log; cp build/layout/lvs.log results/layout_lvs.log; cp build/layout/lvs/adc_core_extracted.cir results/layout_extracted.cir; cp build/layout/generate.log results/layout_generate.log
	if grep -q "DRC Check Passed" results/layout_drc.log && grep -qx "run_drc exit 0" results/layout_drc.log; then c=0; else c=1; fi; $(SAVE) layout_drc $$c results/layout_drc.log results/layout_generate.log
	if grep -q "PASS (netlists match)" results/layout_lvs.log && grep -qx "run_lvs exit 0" results/layout_lvs.log && grep -qx "lvs_names exit 0" results/layout_lvs.log; then c=0; else c=1; fi; $(SAVE) layout_lvs $$c results/layout_lvs.log results/layout_extracted.cir

build/layout/adc_core_pex.spice: build/layout/adc_core.gds layout/extract.tcl
	cd build/layout && $(RUN) bash -c 'magic -dnull -noconsole -rcfile $$PDK_ROOT/$$PDK/libs.tech/magic/ihp-sg13g2.magicrc ../../layout/extract.tcl' > extract.log 2>&1

build/post_layout/%/convert.txt: tests/convert.cir build/layout/adc_core_pex.spice build/sar_logic.so
	mkdir -p $(@D)
	cp $^ $(@D)
	printf '.param n_samples=%s k_tone=%s\n' $(N) $(K) > $(@D)/tone.inc
	$(call corner,$(word 1,$(subst _, ,$*)),$(word 2,$(subst _, ,$*)),$(word 3,$(subst _, ,$*)),0) > $(@D)/corner.inc
	printf '.include adc_core_pex.spice\n.subckt adc_core top vin vcm vref_hi vref_lo samp cal d7 d6 d5 d4 d3 d2 d1 d0 t6 t5 t4 t3 t2 t1 t0 cclk cmp cmpn vdd vss\nX1 %s adc_core_pex\n.ends\n' \
	  "$$(sed -n '/^.subckt adc_core_pex/,/^[^.+]/p' $(@D)/adc_core_pex.spice | grep -v '^[^.+]' | sed 's/^.subckt adc_core_pex //; s/^+ //' | tr '\n' ' ')" > $(@D)/core.cir
	sed -i -e '/^.include comparator_sizes.inc$$/d' -e '/^.include cap_dac_sizes.inc$$/d' -e '/^.include comparator.cir$$/d' -e 's/^.include cap_dac.cir$$/.include core.cir/' -e '/^XCMP /d' \
	  -e 's/^XDAC top vin vcm vref_hi vref_lo samp cal a7 a6 a5 a4 a3 a2 a1 a0 t6 t5 t4 t3 t2 t1 t0 vdd 0 cap_dac_cal$$/XCORE top vin vcm vref_hi vref_lo samp cal a7 a6 a5 a4 a3 a2 a1 a0 t6 t5 t4 t3 t2 t1 t0 cclk cmp cmpn vdd 0 adc_core/' $(@D)/convert.cir
	grep -q '^XCORE ' $(@D)/convert.cir
	cd $(@D) && $(RUN) ngspice -b convert.cir > convert.log 2>&1

post_layout: $(POST) $(foreach c,$(LAYOUT_CORNERS),build/convert/$(c)/convert.txt)
	mkdir -p results
	cp build/layout/adc_core_pex.spice results/adc_core_pex.spice
	for c in $(LAYOUT_CORNERS); do cp build/post_layout/$$c/convert.txt results/post_layout_$$c.txt; cp build/post_layout/$$c/measure.txt results/post_layout_measure_$$c.txt; done
	if { $(LOGS) $(POST:.txt=.log) && for c in $(LAYOUT_CORNERS); do echo "schematic $$c:"; $(PY) $(ROOT)/helpers/adc_trim.py code 1.2 build/convert/$$c/convert.txt; $(PY) $(ROOT)/helpers/adc_results.py convert 1.2 $(N) build/convert/$$c/convert.txt build/convert/$$c/measure.txt; s=$$?; \
	  echo "schematic $$c convert check exit $$s (its verdict is the convert target's)"; echo "extracted layout $$c:"; $(PY) $(ROOT)/helpers/adc_trim.py code 1.2 results/post_layout_$$c.txt && $(PY) $(ROOT)/helpers/adc_results.py convert 1.2 $(N) results/post_layout_$$c.txt results/post_layout_measure_$$c.txt || exit 1; done; } > results/post_layout.log 2>&1; then c=0; else c=$$?; fi; \
	  $(SAVE) post_layout $$c results/post_layout.log results/post_layout_*.txt results/adc_core_pex.spice

.PHONY: all sar logic decide offset levels trim uic_check convert supply_corners ramp supplied refs supply_wave shunt_check gear_check ktc model supply_current fom broken review layout post_layout
.DELETE_ON_ERROR:
