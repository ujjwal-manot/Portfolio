# bandgap_ldo commands: make pnp | corners | mc | startup | all
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
STARTUP := $(foreach r,$(RAMPS),$(foreach c,$(PROCESS) tt_m40 tt_125,build/startup/$(c)_$(r)/startup.txt))

all: pnp corners mc startup

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

.PHONY: all pnp corners mc startup
.DELETE_ON_ERROR:
