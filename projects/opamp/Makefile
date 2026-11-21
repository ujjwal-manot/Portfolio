# opamp commands: make charts | sizing | check_model | corners | all
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
ROOT := $(shell git rev-parse --show-toplevel)
RUN := $(ROOT)/setup/run.sh
PY := $(RUN) env PYTHONPATH=$(ROOT)/helpers python3
SAVE := $(RUN) python3 $(ROOT)/helpers/save_result.py results/summary.json
CHARTS := $(foreach c,tt ss ff sf fs,$(foreach t,m40 27 125,build/charts/$(c)_$(t)/charts.txt))
CORNERS := $(foreach c,tt ss ff sf fs,$(foreach t,m40 27 125,$(foreach v,lo nom hi,build/corners/$(c)_$(t)_$(v)/result.txt)))
TESTS := loop step noise swing
PASSIVE_tt := typ
PASSIVE_sf := typ
PASSIVE_fs := typ
PASSIVE_ss := wcs
PASSIVE_ff := bcs
VOLT_lo := 1.08
VOLT_nom := 1.2
VOLT_hi := 1.32

all: charts sizing check_model corners

charts: $(CHARTS)
	mkdir -p results
	for f in $(CHARTS); do cp $$f results/charts_$$(basename $$(dirname $$f)).txt; done
	if $(PY) $(ROOT)/helpers/transistor_charts.py results/charts_*.txt > results/charts.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) charts $$c results/charts.log results/charts_*.txt

sizing: build/sizes.inc

build/sizes.inc: results/charts_tt_27.txt
	mkdir -p build
	if $(PY) $(ROOT)/helpers/opamp_sizing.py $< $@ > results/sizing.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) sizing $$c results/sizing.log

check_model: build/model/result.txt
	cp $< results/model.txt
	if $(PY) $(ROOT)/helpers/analog_results.py model results/model.txt > results/check_model.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) check_model $$c results/check_model.log results/model.txt

corners: $(CORNERS)
	for f in $(CORNERS); do cp $$f results/corner_$$(basename $$(dirname $$f)).txt; done
	if $(PY) $(ROOT)/helpers/analog_results.py corners results/corner_*.txt > results/corners.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) corners $$c results/corners.log results/corner_*.txt

build/model/result.txt: tests/model.cir tests/loop.cir build/sizes.inc
	mkdir -p $(@D)
	cp tests/loop.cir build/sizes.inc $(@D)
	cp tests/model.cir $(@D)/dut.cir
	printf '.lib cornerMOSlv.lib mos_tt\n.lib cornerRES.lib res_typ\n.lib cornerCAP.lib cap_typ\n.temp 27\n.param vsupply=1.2\n' > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b loop.cir > loop.log 2>&1
	cat $(@D)/loop.txt > $@

build/corners/%/result.txt: $(addprefix tests/,$(addsuffix .cir,$(TESTS))) design/opamp.cir build/sizes.inc
	mkdir -p $(@D)
	cp $(addprefix tests/,$(addsuffix .cir,$(TESTS))) build/sizes.inc $(@D)
	cp design/opamp.cir $(@D)/dut.cir
	m=$(word 1,$(subst _, ,$*)); t=$(subst m,-,$(word 2,$(subst _, ,$*))); v=$(word 3,$(subst _, ,$*)); \
	  p=$(PASSIVE_$(word 1,$(subst _, ,$*))); \
	  printf '.lib cornerMOSlv.lib mos_%s\n.lib cornerRES.lib res_%s\n.lib cornerCAP.lib cap_%s\n.temp %s\n.param vsupply=%s\n' $$m $$p $$p $$t $(VOLT_$(word 3,$(subst _, ,$*))) > $(@D)/corner.inc
	cd $(@D) && for t in $(TESTS); do $(RUN) ngspice -b $$t.cir > $$t.log 2>&1; done
	cat $(addprefix $(@D)/,$(addsuffix .txt,$(TESTS))) > $@

build/charts/%/charts.txt: tests/charts.cir
	mkdir -p $(@D)
	cp $< $(@D)
	printf '.lib cornerMOSlv.lib mos_%s\n.temp %s\n' $(word 1,$(subst _, ,$*)) $(subst m,-,$(word 2,$(subst _, ,$*))) > $(@D)/corner.inc
	rm -f $@
	cd $(@D) && $(RUN) ngspice -b charts.cir > ngspice.log 2>&1

.PHONY: all charts sizing check_model corners
.DELETE_ON_ERROR:
