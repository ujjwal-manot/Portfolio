# opamp commands: make charts | all
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
ROOT := $(shell git rev-parse --show-toplevel)
RUN := $(ROOT)/setup/run.sh
SAVE := $(RUN) python3 $(ROOT)/helpers/save_result.py results/summary.json
CHARTS := $(foreach c,tt ss ff sf fs,$(foreach t,m40 27 125,build/charts/$(c)_$(t)/charts.txt))

all: charts

charts: $(CHARTS)
	mkdir -p results
	for f in $(CHARTS); do cp $$f results/charts_$$(basename $$(dirname $$f)).txt; done
	if $(RUN) python3 $(ROOT)/helpers/transistor_charts.py results/charts_*.txt > results/charts.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) charts $$c results/charts.log results/charts_*.txt

build/charts/%/charts.txt: tests/charts.cir
	mkdir -p $(@D)
	cp $< $(@D)
	printf '.lib cornerMOSlv.lib mos_%s\n.temp %s\n' $(word 1,$(subst _, ,$*)) $(subst m,-,$(word 2,$(subst _, ,$*))) > $(@D)/corner.inc
	rm -f $@
	cd $(@D) && $(RUN) ngspice -b charts.cir > ngspice.log 2>&1

.PHONY: all charts
.DELETE_ON_ERROR:
