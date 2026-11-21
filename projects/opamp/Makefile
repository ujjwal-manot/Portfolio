# opamp commands: make charts | sizing | check_model | corners | mc | broken | review | all
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
ROOT := $(shell git rev-parse --show-toplevel)
RUN := $(ROOT)/setup/run.sh
PY := $(RUN) env PYTHONPATH=$(ROOT)/helpers python3
SAVE := $(RUN) python3 $(ROOT)/helpers/save_result.py results/summary.json
CHARTS := $(foreach c,tt ss ff sf fs,$(foreach t,m40 27 125,build/charts/$(c)_$(t)/charts.txt))
CORNERS := $(foreach c,tt ss ff sf fs,$(foreach t,m40 27 125,$(foreach v,lo min nom hi,build/corners/$(c)_$(t)_$(v)/result.txt)))
MC := $(foreach n,$(shell seq 1 200),build/mc/$(n)/result.txt)
TESTS := loop step noise swing load
DAC := $(ROOT)/projects/adc/design/cap_dac.cir $(ROOT)/projects/adc/design/cap_dac_sizes.inc
PASSIVE_tt := typ
PASSIVE_sf := typ
PASSIVE_fs := typ
PASSIVE_ss := wcs
PASSIVE_ff := bcs
VOLT_lo := 1.08
VOLT_min := 1.16
VOLT_nom := 1.2
VOLT_hi := 1.32

all: charts sizing check_model corners mc broken review

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

mc: $(MC)
	for f in $(MC); do cp $$f results/mc_$$(basename $$(dirname $$f)).txt; done
	if $(PY) $(ROOT)/helpers/analog_results.py mc results/mc_*.txt > results/mc.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) mc $$c results/mc.log results/mc_*.txt

broken: build/sizes.inc
	for p in broken/*.patch; do n=$$(basename $$p .patch); d=build/broken/$$n; mkdir -p $$d; cp -r design tests $$d; \
	  patch -s -F0 -d $$d -p1 < $$p; want=$$(sed -n '1s/^Expected failure: //p' $$p); \
	  cp $(addprefix tests/,$(addsuffix .cir,$(TESTS))) $(DAC) build/sizes.inc $$d; cp $$d/design/opamp.cir $$d/dut.cir; \
	  printf '.lib cornerMOSlv.lib mos_tt\n.lib cornerRES.lib res_typ\n.lib cornerCAP.lib cap_typ\n.temp 27\n.param vsupply=1.2\n.param mm=0\n' > $$d/corner.inc; \
	  (cd $$d && for t in $(TESTS); do $(RUN) ngspice -b $$t.cir > $$t.log 2>&1; done; cat $(addsuffix .txt,$(TESTS)) > corner_tt_27_nom.txt); \
	  cp $$d/corner_tt_27_nom.txt results/broken_$$n.txt; \
	  if $(PY) $(ROOT)/helpers/analog_results.py corners results/broken_$$n.txt > results/broken_$$n.log 2>&1; then c=1; \
	  elif [ -n "$$want" ] && grep -qxF -- "$$want" results/broken_$$n.log; then c=0; else c=2; fi; \
	  $(SAVE) broken_$$n $$c results/broken_$$n.log results/broken_$$n.txt; done

REVIEW := tt_27_nom ss_125_lo sf_125_lo ff_m40_lo ff_125_hi ss_125_min

review: build/sizes.inc $(addprefix build/corners/,$(addsuffix /result.txt,$(REVIEW)))
	for v in opamp opamp_indirect; do for c in $(REVIEW); do d=build/review/$$v/$$c; mkdir -p $$d; \
	  cp $(addprefix tests/,$(addsuffix .cir,$(TESTS))) $(DAC) build/sizes.inc build/corners/$$c/corner.inc $$d; cp design/$$v.cir $$d/dut.cir; \
	  (cd $$d && for t in $(TESTS); do $(RUN) ngspice -b $$t.cir > $$t.log 2>&1; done; cat $(addsuffix .txt,$(TESTS)) > result.txt); \
	  cp $$d/result.txt results/review_$${v}_$$c.txt; done; \
	  if $(PY) $(ROOT)/helpers/analog_results.py corners $$(for c in $(REVIEW); do echo results/review_$${v}_$$c.txt; done) > results/review_$$v.log 2>&1; then c=0; else c=$$?; fi; echo "analog_results exit $$c" >> results/review_$$v.log; done
	if grep -q "every corner meets every spec" results/review_opamp.log; then c=0; else c=1; fi; $(SAVE) review $$c results/review_opamp.log results/review_opamp_indirect.log results/review_*_*.txt

build/model/result.txt: tests/model.cir tests/loop.cir build/sizes.inc
	mkdir -p $(@D)
	cp tests/loop.cir build/sizes.inc $(@D)
	cp tests/model.cir $(@D)/dut.cir
	printf '.lib cornerMOSlv.lib mos_tt\n.lib cornerRES.lib res_typ\n.lib cornerCAP.lib cap_typ\n.temp 27\n.param vsupply=1.2\n' > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b loop.cir > loop.log 2>&1
	cat $(@D)/loop.txt > $@

build/corners/%/result.txt: $(addprefix tests/,$(addsuffix .cir,$(TESTS))) $(DAC) design/opamp.cir build/sizes.inc
	mkdir -p $(@D)
	cp $(addprefix tests/,$(addsuffix .cir,$(TESTS))) $(DAC) build/sizes.inc $(@D)
	cp design/opamp.cir $(@D)/dut.cir
	p=$(PASSIVE_$(word 1,$(subst _, ,$*))); \
	  printf '.lib cornerMOSlv.lib mos_%s\n.lib cornerRES.lib res_%s\n.lib cornerCAP.lib cap_%s\n.temp %s\n.param vsupply=%s\n.param mm=0\n' \
	  $(word 1,$(subst _, ,$*)) $$p $$p $(subst m,-,$(word 2,$(subst _, ,$*))) $(VOLT_$(word 3,$(subst _, ,$*))) > $(@D)/corner.inc
	cd $(@D) && for t in $(TESTS); do $(RUN) ngspice -b $$t.cir > $$t.log 2>&1; done
	cat $(addprefix $(@D)/,$(addsuffix .txt,$(TESTS))) > $@

build/mc/%/result.txt: tests/loop.cir tests/step.cir tests/swing.cir tests/load.cir $(DAC) design/opamp.cir build/sizes.inc
	mkdir -p $(@D)
	cp tests/loop.cir tests/step.cir tests/swing.cir tests/load.cir $(DAC) build/sizes.inc $(@D)
	cp design/opamp.cir $(@D)/dut.cir
	printf '.lib cornerMOSlv.lib mos_tt_mismatch\n.lib cornerRES.lib res_typ_mismatch\n.lib cornerCAP.lib cap_typ_mismatch\n.temp 27\n.param vsupply=1.2\n.param mm=1\n.option seed=%s\n' $* > $(@D)/corner.inc
	cd $(@D) && for t in loop step swing load; do $(RUN) ngspice -b $$t.cir > $$t.log 2>&1; done
	cat $(@D)/loop.txt $(@D)/step.txt $(@D)/swing.txt $(@D)/load.txt > $@

build/charts/%/charts.txt: tests/charts.cir
	mkdir -p $(@D)
	cp $< $(@D)
	printf '.lib cornerMOSlv.lib mos_%s\n.temp %s\n' $(word 1,$(subst _, ,$*)) $(subst m,-,$(word 2,$(subst _, ,$*))) > $(@D)/corner.inc
	rm -f $@
	cd $(@D) && $(RUN) ngspice -b charts.cir > ngspice.log 2>&1

.PHONY: all charts sizing check_model corners mc broken review
.DELETE_ON_ERROR:
