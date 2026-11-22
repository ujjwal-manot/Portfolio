# opamp commands: make charts | sizing | check_model | corners | mc | mc_hot | broken | review | layout | post_layout | all
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
ROOT := $(shell git rev-parse --show-toplevel)
RUN := $(ROOT)/setup/run.sh
PY := $(RUN) env PYTHONPATH=$(ROOT)/helpers python3
SAVE := $(RUN) python3 $(ROOT)/helpers/save_result.py results/summary.json
CHARTS := $(foreach c,tt ss ff sf fs,$(foreach t,m40 27 125,build/charts/$(c)_$(t)/charts.txt))
CORNERS := $(foreach c,tt ss ff sf fs,$(foreach t,m40 27 125,$(foreach v,lo min nom hi,build/corners/$(c)_$(t)_$(v)/result.txt)))
MC := $(foreach n,$(shell seq 1 200),build/mc/$(n)/result.txt)
MC_HOT := $(foreach n,$(shell seq 1 100),build/mc_hot/$(n)/result.txt)
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

all: charts sizing check_model corners mc mc_hot broken review layout post_layout

charts: $(CHARTS)
	mkdir -p results
	for f in $(CHARTS); do cp $$f results/charts_$$(basename $$(dirname $$f)).txt; done
	if $(PY) $(ROOT)/helpers/transistor_charts.py results/charts_*.txt > results/charts.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) charts $$c results/charts.log results/charts_*.txt

sizing: build/sizes.inc

build/sizes.inc: results/charts_tt_27.txt $(ROOT)/helpers/opamp_sizing.py
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

mc_hot: $(MC_HOT)
	for f in $(MC_HOT); do cp $$f results/mchot_$$(basename $$(dirname $$f)).txt; done
	if $(PY) $(ROOT)/helpers/analog_results.py mc results/mchot_*.txt > results/mc_hot.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) mc_hot $$c results/mc_hot.log results/mchot_*.txt

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

build/layout/opamp.gds: layout/opamp.py $(ROOT)/helpers/row_layout.py design/opamp.cir build/sizes.inc
	mkdir -p build/layout
	$(RUN) env SIZES=build/sizes.inc OUT=build/layout klayout -b -r layout/opamp.py > build/layout/generate.log 2>&1

layout: build/layout/opamp.gds
	mkdir -p results
	rm -rf build/layout/drc build/layout/lvs
	cd build/layout && if $(RUN) bash -c 'python3 $$PDK_ROOT/$$PDK/libs.tech/klayout/tech/drc/run_drc.py --path=opamp.gds --topcell=opamp --run_dir=drc --no_density' > drc.log 2>&1; then e=0; else e=$$?; fi; echo "run_drc exit $$e" >> drc.log
	cd build/layout && if $(RUN) bash -c 'python3 $$PDK_ROOT/$$PDK/libs.tech/klayout/tech/lvs/run_lvs.py --layout=opamp.gds --netlist=opamp.cdl --topcell=opamp --run_dir=lvs --combine_devices --disable_tap_extraction' > lvs.log 2>&1; then e=0; else e=$$?; fi; echo "run_lvs exit $$e" >> lvs.log
	cd build/layout && if $(RUN) klayout -b -rd path=lvs/opamp.lvsdb -r $(ROOT)/helpers/lvs_names.py >> lvs.log 2>&1; then e=0; else e=$$?; fi; echo "lvs_names exit $$e" >> lvs.log
	cp build/layout/drc.log results/layout_drc.log; cp build/layout/lvs.log results/layout_lvs.log; cp build/layout/lvs/opamp_extracted.cir results/layout_extracted.cir
	if grep -q "DRC Check Passed" results/layout_drc.log && grep -qx "run_drc exit 0" results/layout_drc.log; then c=0; else c=1; fi; $(SAVE) layout_drc $$c results/layout_drc.log
	if grep -q "PASS (netlists match)" results/layout_lvs.log && grep -qx "run_lvs exit 0" results/layout_lvs.log && grep -qx "lvs_names exit 0" results/layout_lvs.log; then c=0; else c=1; fi; $(SAVE) layout_lvs $$c results/layout_lvs.log results/layout_extracted.cir

build/layout/opamp_pex.spice: build/layout/opamp.gds layout/extract.tcl
	cd build/layout && $(RUN) bash -c 'magic -dnull -noconsole -rcfile $$PDK_ROOT/$$PDK/libs.tech/magic/ihp-sg13g2.magicrc ../../layout/extract.tcl' > extract.log 2>&1

post_layout: build/layout/opamp_pex.spice build/sizes.inc $(addprefix build/corners/,$(addsuffix /result.txt,$(REVIEW)))
	mkdir -p results
	cp build/layout/opamp_pex.spice results/opamp_pex.spice
	for c in $(REVIEW); do d=build/post_layout/$$c; mkdir -p $$d; \
	  cp $(addprefix tests/,$(addsuffix .cir,$(TESTS))) $(DAC) build/sizes.inc build/corners/$$c/corner.inc build/layout/opamp_pex.spice $$d; \
	  printf '.include opamp_pex.spice\n.subckt opamp inp inn out vdd vss ibias\nX1 %s opamp_pex\n.ends\n' "$$(sed -n 's/^.subckt opamp_pex //p' build/layout/opamp_pex.spice)" > $$d/dut.cir; \
	  (cd $$d && for t in $(TESTS); do $(RUN) ngspice -b $$t.cir > $$t.log 2>&1; done; cat $(addsuffix .txt,$(TESTS)) > result.txt); \
	  cp $$d/result.txt results/post_layout_$$c.txt; done
	if $(PY) $(ROOT)/helpers/analog_results.py corners $(foreach c,$(REVIEW),results/post_layout_$(c).txt) > results/post_layout.log 2>&1; then c=0; else c=$$?; fi; \
	  $(SAVE) post_layout $$c results/post_layout.log results/post_layout_*.txt results/opamp_pex.spice

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
	printf '.lib cornerMOSlv.lib mos_tt\n.lib cornerRES.lib res_typ\n.lib cornerCAP.lib cap_typ\n.temp 27\n.param vsupply=1.2\n.param mm=0\n' > $(@D)/corner.inc
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

build/mc_hot/%/result.txt: tests/loop.cir tests/step.cir tests/swing.cir tests/load.cir $(DAC) design/opamp.cir build/sizes.inc
	mkdir -p $(@D)
	cp tests/loop.cir tests/step.cir tests/swing.cir tests/load.cir $(DAC) build/sizes.inc $(@D)
	cp design/opamp.cir $(@D)/dut.cir
	printf '.lib cornerMOSlv.lib mos_ff_mismatch\n.lib cornerRES.lib res_bcs_mismatch\n.lib cornerCAP.lib cap_bcs_mismatch\n.temp 125\n.param vsupply=1.32\n.param mm=1\n.option seed=%s\n' $* > $(@D)/corner.inc
	cd $(@D) && for t in loop step swing load; do $(RUN) ngspice -b $$t.cir > $$t.log 2>&1; done
	cat $(@D)/loop.txt $(@D)/step.txt $(@D)/swing.txt $(@D)/load.txt > $@

build/charts/%/charts.txt: tests/charts.cir
	mkdir -p $(@D)
	cp $< $(@D)
	printf '.lib cornerMOSlv.lib mos_%s\n.temp %s\n' $(word 1,$(subst _, ,$*)) $(subst m,-,$(word 2,$(subst _, ,$*))) > $(@D)/corner.inc
	rm -f $@
	cd $(@D) && $(RUN) ngspice -b charts.cir > ngspice.log 2>&1

.PHONY: layout post_layout all charts sizing check_model corners mc mc_hot broken review
.DELETE_ON_ERROR:
