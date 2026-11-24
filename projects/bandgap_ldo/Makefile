# bandgap_ldo commands: make pnp | corners | mc | startup | ldo_model | ldo | bleed_study | ldo_mc | all
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
ROOT := $(shell git rev-parse --show-toplevel)
RUN := $(ROOT)/setup/run.sh
PY := $(RUN) env PYTHONPATH=$(ROOT)/helpers python3
SAVE := $(RUN) python3 $(ROOT)/helpers/save_result.py results/summary.json
PROCESS := tt ss ff sf fs
VOLTS := 3v0 3v3 3v6
VOLT_3v0 := 3.0
VOLT_3v3 := 3.3
VOLT_3v6 := 3.6
PASSIVE_tt := typ
PASSIVE_sf := typ
PASSIVE_fs := typ
PASSIVE_ss := wcs
PASSIVE_ff := bcs
RAMPS := 10n 1u 100u 1m
BANDGAP := design/bandgap.cir design/bandgap_sizes.inc
CORNERS := $(foreach p,$(PROCESS),$(foreach v,$(VOLTS),build/corners/$(p)_$(v)/dc.txt))
MC := $(foreach n,$(shell seq 1 200),build/mc/$(n)/dc.txt)
LDO := design/ldo.cir design/ldo_sizes.inc
LDO_TESTS := tests/ldo_dc.cir tests/ldo_psrr.cir tests/ldo_step.cir tests/ldo_startup.cir tests/loop.cir
LDO_CORNERS := tt_3v3_27 $(foreach p,$(PROCESS),$(foreach v,3v0 3v6,$(foreach t,m40 125,$(p)_$(v)_$(t))))
LDO_RESULTS := $(foreach c,$(LDO_CORNERS),build/ldo/$(c)/result.txt)
STARTUP := $(foreach r,$(RAMPS),$(foreach c,$(PROCESS) tt_m40 tt_125,build/startup/$(c)_$(r)/startup.txt))

all: pnp corners mc startup ldo_model ldo bleed_study ldo_mc
LDO_MC := $(foreach k,ss ff,$(foreach n,$(shell seq 1 50),build/ldo_mc/$(k)_$(n)/mc.txt))
STUDY_CORNERS := tt_3v3_27 ff_3v6_125 ss_3v0_125

corner = printf '.lib cornerMOShv.lib mos_%s\n.lib cornerHBT.lib hbt_%s\n.lib cornerRES.lib res_%s\n.lib cornerCAP.lib cap_%s\n.temp %s\n.param vsupply=%s\n.param mm=0\n' $(1) $(PASSIVE_$(1)) $(PASSIVE_$(1)) $(PASSIVE_$(1)) $(2) $(3)

pnp:
	mkdir -p build/pnp results
	cp tests/pnp.cir build/pnp
	if (cd build/pnp && $(RUN) ngspice -b pnp.cir > pnp.log 2>&1); then c=0; else c=$$?; fi; cp build/pnp/pnp.txt results/pnp.txt; $(SAVE) pnp $$c results/pnp.txt

corners: $(CORNERS)
	mkdir -p results
	for f in $(CORNERS); do cp $$f results/dc_$$(basename $$(dirname $$f)).txt; done
	if $(PY) $(ROOT)/helpers/bandgap_results.py corners results/dc_*_*.txt > results/corners.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) corners $$c results/corners.log results/dc_*_*.txt

mc: $(MC)
	mkdir -p results
	for f in $(MC); do cp $$f results/mc_$$(basename $$(dirname $$f)).txt; done
	if $(PY) $(ROOT)/helpers/bandgap_results.py mc results/mc_*.txt > results/mc.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) mc $$c results/mc.log results/mc_*.txt

startup: $(STARTUP)
	mkdir -p results
	for f in $(STARTUP); do cp $$f results/startup_$$(basename $$(dirname $$f)).txt; done
	if $(PY) $(ROOT)/helpers/bandgap_results.py startup results/startup_*.txt > results/startup.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) startup $$c results/startup.log results/startup_*.txt

build/corners/%/dc.txt: tests/dc.cir $(BANDGAP)
	mkdir -p $(@D)
	cp $^ $(@D)
	$(call corner,$(word 1,$(subst _, ,$*)),27,$(VOLT_$(word 2,$(subst _, ,$*)))) > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b dc.cir > dc.log 2>&1

build/mc/%/dc.txt: tests/dc.cir $(BANDGAP)
	mkdir -p $(@D)
	cp $^ $(@D)
	printf '.lib cornerMOShv.lib mos_tt_mismatch\n.lib cornerHBT.lib hbt_typ_mismatch\n.lib cornerRES.lib res_typ_mismatch\n.lib cornerCAP.lib cap_typ_mismatch\n.temp 27\n.param vsupply=3.3\n.param mm=1\n.option seed=%s\n' $* > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b dc.cir > dc.log 2>&1

build/startup/%/startup.txt: tests/startup.cir $(BANDGAP)
	mkdir -p $(@D)
	cp $^ $(@D)
	n=$*; ramp=$${n##*_}; c=$${n%_*}; p=$${c%%_*}; t=27; case $$c in *_m40) t=-40;; *_125) t=125;; esac; \
	  q=typ; case $$p in ss) q=wcs;; ff) q=bcs;; esac; \
	  printf '.lib cornerMOShv.lib mos_%s\n.lib cornerHBT.lib hbt_%s\n.lib cornerRES.lib res_%s\n.lib cornerCAP.lib cap_%s\n.temp %s\n.param vsupply=3.3\n.param mm=0\n' $$p $$q $$q $$q $$t > $(@D)/corner.inc; \
	  echo ".param ramp=$$ramp" > $(@D)/ramp.inc
	cd $(@D) && $(RUN) ngspice -b startup.cir > startup.log 2>&1

ldo_model: tests/loop.cir tests/tian_model.cir $(BANDGAP)
	mkdir -p build/ldo_model results
	cp tests/loop.cir $(BANDGAP) design/ldo_sizes.inc build/ldo_model
	cp tests/tian_model.cir build/ldo_model/ldo.cir
	$(call corner,tt,27,3.3) > build/ldo_model/corner.inc
	echo ".param iload=0" > build/ldo_model/load.inc
	cd build/ldo_model && $(RUN) ngspice -b loop.cir > loop.log 2>&1
	cp build/ldo_model/loop.txt results/ldo_model.txt
	if $(PY) $(ROOT)/helpers/ldo_results.py model results/ldo_model.txt > results/ldo_model.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) ldo_model $$c results/ldo_model.log results/ldo_model.txt

ldo: $(LDO_RESULTS)
	mkdir -p results
	for c in $(LDO_CORNERS); do cp build/ldo/$$c/result.txt results/ldo_$$c.txt; done
	if $(PY) $(ROOT)/helpers/ldo_results.py corners results/ldo_*_*_*.txt > results/ldo.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) ldo $$c results/ldo.log results/ldo_*_*_*.txt

build/ldo/%/result.txt: $(LDO_TESTS) $(BANDGAP) $(LDO)
	mkdir -p $(@D)
	cp $^ $(@D)
	p=$$(echo $* | cut -d_ -f1); v=$$(echo $* | cut -d_ -f2 | tr v .); t=$$(echo $* | cut -d_ -f3 | sed 's/m/-/'); \
	  q=typ; case $$p in ss) q=wcs;; ff) q=bcs;; esac; \
	  printf '.lib cornerMOShv.lib mos_%s\n.lib cornerHBT.lib hbt_%s\n.lib cornerRES.lib res_%s\n.lib cornerCAP.lib cap_%s\n.temp %s\n.param vsupply=%s\n.param mm=0\n' $$p $$q $$q $$q $$t $$v > $(@D)/corner.inc
	cd $(@D) && echo ".param ramp=10n" > ramp.inc && $(RUN) ngspice -b ldo_dc.cir > ldo_dc.log 2>&1 && $(RUN) ngspice -b ldo_psrr.cir > ldo_psrr.log 2>&1 && $(RUN) ngspice -b ldo_startup.cir > ldo_startup.log 2>&1; \
	  for s in 0p5m 2m; do echo ".param istep=$$(echo $$s | tr p .)" > step.inc; $(RUN) ngspice -b ldo_step.cir > step_$$s.log 2>&1; sed "s/^step /step_$$s /" step.txt > step_$$s.txt; done; \
	  for l in 0 250u 1m 2m; do echo ".param iload=$$l" > load.inc; $(RUN) ngspice -b loop.cir > loop_$$l.log 2>&1; sed "s/^loop /loop_$$l /" loop.txt > loop_$$l.txt; done; \
	  cat ldo_dc.txt psrr.txt step_0p5m.txt step_2m.txt loop_*.txt ldo_startup.txt > result.txt

bleed_study: ldo
	mkdir -p build/study results
	cp -r design tests Makefile build/study
	patch -s -F0 -d build/study -p1 < study/resistor_bleed.patch
	$(MAKE) -C build/study $(foreach c,$(STUDY_CORNERS),build/ldo/$(c)/result.txt) > build/study/make.log 2>&1
	for c in $(STUDY_CORNERS); do cp build/study/build/ldo/$$c/result.txt results/bleed_study_$$c.txt; done
	if $(PY) $(ROOT)/helpers/ldo_results.py study $(foreach c,$(STUDY_CORNERS),results/ldo_$(c).txt) $(foreach c,$(STUDY_CORNERS),results/bleed_study_$(c).txt) > results/bleed_study.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) bleed_study $$c results/bleed_study.log results/bleed_study_*.txt

build/ldo_mc/%/mc.txt: tests/ldo_mc.cir $(BANDGAP) $(LDO)
	mkdir -p $(@D)
	cp $^ $(@D)
	k=$$(echo $* | cut -d_ -f1); n=$$(echo $* | cut -d_ -f2); q=wcs; v=3.0; if [ $$k = ff ]; then q=bcs; v=3.6; fi; \
	  printf '.lib cornerMOShv.lib mos_%s_mismatch\n.lib cornerHBT.lib hbt_%s_mismatch\n.lib cornerRES.lib res_%s_mismatch\n.lib cornerCAP.lib cap_%s_mismatch\n.temp 125\n.param vsupply=%s\n.param mm=1\n.option seed=%s\n' $$k $$q $$q $$q $$v $$n > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b ldo_mc.cir > mc.log 2>&1

ldo_mc: $(LDO_MC)
	mkdir -p results
	for f in $(LDO_MC); do cp $$f results/ldo_mc_$$(basename $$(dirname $$f)).txt; done
	for k in ss ff; do if $(PY) $(ROOT)/helpers/ldo_results.py mc $$k results/ldo_mc_$${k}_*.txt > results/ldo_mc_$$k.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) ldo_mc_$$k $$c results/ldo_mc_$$k.log results/ldo_mc_$${k}_*.txt; done

.PHONY: all pnp corners mc startup ldo_model ldo bleed_study ldo_mc
.DELETE_ON_ERROR:
