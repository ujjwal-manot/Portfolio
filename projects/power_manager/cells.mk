# power_manager cell checks: make -f cells.mk cvc | cells_broken
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
ROOT := $(shell git rev-parse --show-toplevel)
RUN := $(ROOT)/setup/run.sh
SAVE := $(RUN) python3 $(ROOT)/helpers/save_result.py results/summary.json
FLAT := python3 $(ROOT)/helpers/spice_flatten.py
CVC_RUNS := shifter_hv_3v6 shifter_hv_3v3 dldo_unit_3v6 dldo_unit_3v3
CELLS_BROKEN := $(basename $(notdir $(wildcard broken/cells_*.patch)))

build/cvc/shifter_hv.cdl: design/shifter_hv.cir design/shifter_hv_sizes.inc
	mkdir -p $(@D)
	$(FLAT) shifter_hv design/shifter_hv_sizes.inc design/shifter_hv.cir > $@

build/cvc/dldo_unit.cdl: design/dldo_unit.cir design/shifter_hv.cir design/dldo_sizes.inc design/shifter_hv_sizes.inc
	mkdir -p $(@D)
	cat design/dldo_sizes.inc design/shifter_hv_sizes.inc > build/cvc/dldo_unit_sizes.inc
	$(FLAT) dldo_unit build/cvc/dldo_unit_sizes.inc design/shifter_hv.cir design/dldo_unit.cir > $@

build/cvc/%/cvc.log: build/cvc/shifter_hv.cdl build/cvc/dldo_unit.cdl cvc/models.txt cvc/shifter_hv.power cvc/dldo_unit.power
	mkdir -p $(@D)
	b=$(patsubst %_3v3,%,$(patsubst %_3v6,%,$*)); v=$(lastword $(subst _, ,$*)); cp build/cvc/$$b.cdl cvc/models.txt $(@D); \
	  sed "s/VIN_MAX/$$(echo $$v | tr v .)/" cvc/$$b.power > $(@D)/power.txt; \
	  printf "CVC_TOP = '%s'\nCVC_NETLIST = '%s.cdl'\nCVC_MODE = '%s'\nCVC_MODEL_FILE = 'models.txt'\nCVC_POWER_FILE = 'power.txt'\nCVC_REPORT_FILE = 'cvc.log'\nCVC_REPORT_TITLE = '%s'\n" $$b $$b $$v $* > $(@D)/cvcrc
	cd $(@D) && $(RUN) cvc_rv cvcrc > run.log 2>&1
	grep -q '^CVC: End:' $@

cvc: $(foreach r,$(CVC_RUNS),build/cvc/$(r)/cvc.log)
	mkdir -p results
	e=0; for r in $(CVC_RUNS); do { cat build/cvc/$$r/cvc.log; zcat build/cvc/$$r/cvc.error.gz; } > results/cvc_$$r.log; \
	  if grep -Eq '^CVC: Total: +0$$' results/cvc_$$r.log; then c=0; else c=1; fi; $(SAVE) cvc_$$r $$c results/cvc_$$r.log || e=1; done; exit $$e

cells_broken:
	mkdir -p results
	e=0; for n in $(CELLS_BROKEN); do p=broken/$$n.patch; d=build/cells_broken/$$n; mkdir -p $$d; cp -r design tests cvc cells.mk $$d; \
	  patch -s -F0 -d $$d -p1 < $$p; want=$$(sed -n '1s/^Expected failure: //p' $$p); run=$$(sed -n '2s/^Run: //p' $$p); log=$$(sed -n '3s/^Log: //p' $$p); \
	  if $(MAKE) -C $$d -f cells.mk $$run > $$d/make.log 2>&1; then c=1; elif [ -n "$$want" ] && grep -qF -- "$$want" $$d/$$log; then c=0; else c=2; fi; \
	  cp $$d/$$log results/$$n.log; $(SAVE) $$n $$c results/$$n.log || e=1; done; exit $$e

.PHONY: cvc cells_broken
.SECONDARY:
