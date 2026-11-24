# power_manager supervisor commands (make -f supervisor.mk): sup_detector | sup_stretch_rtl | sup_por | sup_mc | sup_droop | sup_broken | sup_all
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
ROOT := $(shell git rev-parse --show-toplevel)
RUN := $(ROOT)/setup/run.sh
PY := $(RUN) env PYTHONPATH=$(ROOT)/helpers python3
SAVE := $(RUN) python3 $(ROOT)/helpers/save_result.py results/summary.json
PYTEST := $(RUN) env PYTHONPATH=$(ROOT)/helpers python3 -m pytest -q -s -p no:cacheprovider
BG := $(ROOT)/projects/bandgap_ldo/design
B := build/sup
TEMP_25 := 25
TEMP_27 := 27
TEMP_125 := 125
TEMP_m40 := -40
DET_CORNERS := tt_25 ss_125 ss_m40 ff_m40 ff_125
DET := $(foreach c,$(DET_CORNERS),$(B)/detector/$(c)/detector.txt)
SUP_CORNERS := tt_27 $(foreach p,ss ff sf fs,$(foreach t,m40 125,$(p)_$(t)))
SUP_RAMPS := 10u 1000u
SUP := $(foreach c,$(SUP_CORNERS),$(foreach r,$(SUP_RAMPS),$(B)/por/$(c)_$(r)/sup.txt))
SUP_MC := $(foreach n,$(shell seq 1 100),$(B)/mc/$(n)/sup.txt)
SUP_FILES := tests/supervisor_bench.cir design/supervisor.cir design/supervisor_sizes.inc $(BG)/bandgap.cir $(BG)/bandgap_sizes.inc

sup_all: sup_detector sup_stretch_rtl sup_por sup_mc sup_droop sup_broken

$(B)/stdcell_mm.spice:
	mkdir -p $(@D)
	$(RUN) bash -c 'sed -E "/^X.* sg13_lv_(n|p)mos /s/$$/ mm_ok={mm}/" $$PDK_ROOT/$$PDK/libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice' > $@.tmp
	mv $@.tmp $@

$(B)/detector/%/detector.txt: tests/detector.cir design/droop_detector.cir $(B)/stdcell_mm.spice
	mkdir -p $(@D)
	cp $^ $(@D)
	printf '.lib cornerMOSlv.lib mos_%s\n.temp %s\n.param mm=0\n' $(word 1,$(subst _, ,$*)) $(TEMP_$(word 2,$(subst _, ,$*))) > $(@D)/corner.inc
	rm -f $@
	cd $(@D) && $(ROOT)/helpers/ngspice.sh detector.cir detector.log

sup_detector: $(DET)
	mkdir -p results
	for c in $(DET_CORNERS); do cp $(B)/detector/$$c/detector.txt results/sup_detector_$$c.txt; done
	if $(PY) $(ROOT)/helpers/supervisor_results.py detector $(foreach c,$(DET_CORNERS),results/sup_detector_$(c).txt) > results/sup_detector.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) sup_detector $$c results/sup_detector.log $(foreach c,$(DET_CORNERS),results/sup_detector_$(c).txt)

sup_stretch_rtl:
	mkdir -p results
	if $(PYTEST) tests/test_clock_stretch.py > results/sup_stretch_rtl.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) sup_stretch_rtl $$c results/sup_stretch_rtl.log

$(B)/por/%/sup.txt: $(SUP_FILES)
	mkdir -p $(@D)
	cp $^ $(@D)
	n=$*; r=$${n##*_}; c=$${n%_*}; p=$${c%%_*}; t=$${c#*_}; case $$p in ss) q=wcs;; ff) q=bcs;; *) q=typ;; esac; case $$t in m40) t=-40;; esac; \
	  printf '.lib cornerMOShv.lib mos_%s\n.lib cornerHBT.lib hbt_%s\n.lib cornerRES.lib res_%s\n.lib cornerCAP.lib cap_%s\n.temp %s\n.param mm=0\n' $$p $$q $$q $$q $$t > $(@D)/corner.inc; \
	  echo ".param ramp=$$r" > $(@D)/ramp.inc
	cd $(@D) && $(ROOT)/helpers/ngspice.sh supervisor_bench.cir sup.log

sup_por: $(SUP)
	mkdir -p results
	for c in $(SUP_CORNERS); do for r in $(SUP_RAMPS); do cp $(B)/por/$${c}_$$r/sup.txt results/sup_$${c}_$$r.txt; done; done
	if $(PY) $(ROOT)/helpers/supervisor_results.py supervisor $(foreach c,$(SUP_CORNERS),$(foreach r,$(SUP_RAMPS),results/sup_$(c)_$(r).txt)) > results/sup_por.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) sup_por $$c results/sup_por.log $(foreach c,$(SUP_CORNERS),$(foreach r,$(SUP_RAMPS),results/sup_$(c)_$(r).txt))

$(B)/mc/%/sup.txt: $(SUP_FILES)
	mkdir -p $(@D)
	cp $^ $(@D)
	printf '.lib cornerMOShv.lib mos_tt_mismatch\n.lib cornerHBT.lib hbt_typ_mismatch\n.lib cornerRES.lib res_typ_mismatch\n.lib cornerCAP.lib cap_typ_mismatch\n.temp 27\n.param mm=1\n.option seed=%s\n' $* > $(@D)/corner.inc
	echo ".param ramp=100u" > $(@D)/ramp.inc
	cd $(@D) && $(ROOT)/helpers/ngspice.sh supervisor_bench.cir sup.log

sup_mc: $(SUP_MC)
	mkdir -p results
	for n in $$(seq 1 100); do cp $(B)/mc/$$n/sup.txt results/sup_mc_$${n}_100u.txt; done
	if $(PY) $(ROOT)/helpers/supervisor_results.py mc $$(for n in $$(seq 1 100); do echo results/sup_mc_$${n}_100u.txt; done) > results/sup_mc.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) sup_mc $$c results/sup_mc.log results/sup_mc_*_100u.txt

.PHONY: sup_all sup_detector sup_stretch_rtl sup_por sup_mc sup_droop sup_broken
