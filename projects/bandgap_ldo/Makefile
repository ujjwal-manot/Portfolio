# bandgap_ldo commands: make pnp | corners | mc | startup | ldo_model | ldo | bleed_study | ldo_mc | broken | layout | post_layout | all
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

all: pnp corners mc startup ldo_model ldo bleed_study ldo_mc broken layout post_layout
LDO_MC := $(foreach k,ss ff,$(foreach n,$(shell seq 1 50),build/ldo_mc/$(k)_$(n)/mc.txt))
STUDY_CORNERS := tt_3v3_27 ff_3v6_125 ss_3v0_125
BLOCKS := bandgap ldo
NAMES_bandgap := a,e8,e3
POST_BG := tt_3v3 ss_3v0 ff_3v6
POST_LDO := tt_3v3_27 ss_3v0_125 ff_3v6_m40

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

broken:
	rm -rf build/broken
	mkdir -p results build/broken
	for p in broken/*.patch; do n=$$(basename $$p .patch); d=build/broken/$$n; mkdir -p $$d; cp -r design tests study layout Makefile $$d; \
	  patch -s -F0 -d $$d -p1 < $$p; want=$$(sed -n '1s/^Expected failure: //p' $$p); run=$$(sed -n '2s/^Run: //p' $$p); \
	  log=$$(sed -n '3s/^Log: //p' $$p); [ -n "$$log" ] || log=results/$${run%% *}.log; \
	  if $(MAKE) -C $$d $$run > $$d/make.log 2>&1; then c=1; elif [ -n "$$want" ] && grep -qF -- "$$want" $$d/$$log; then c=0; else c=2; fi; \
	  cp $$d/$$log results/broken_$$n.log; $(SAVE) broken_$$n $$c results/broken_$$n.log; done

build/layout/%.cdl: design/%.cir $(BANDGAP) $(LDO) $(ROOT)/helpers/spice_flatten.py
	mkdir -p build/layout
	cat design/bandgap_sizes.inc design/ldo_sizes.inc > build/layout/sizes.inc
	python3 $(ROOT)/helpers/spice_flatten.py $* build/layout/sizes.inc $< > $@

build/layout/%.gds: build/layout/%.cdl layout/%.py $(ROOT)/helpers/hv_layout.py $(ROOT)/helpers/row_layout.py
	$(RUN) env HELPERS=$(ROOT)/helpers NETLIST=build/layout/$*.cdl OUT=build/layout klayout -b -r layout/$*.py > build/layout/generate_$*.log 2>&1

layout: $(foreach b,$(BLOCKS),build/layout/$(b).gds build/layout/$(b).cdl)
	rm -rf build/layout/checks
	mkdir -p results build/layout/checks
	for b in $(BLOCKS); do d=build/layout/checks/$$b; mkdir -p $$d; cp build/layout/$$b.gds build/layout/$$b.cdl $$d; \
	  if (cd $$d && $(RUN) bash -c "python3 \$$PDK_ROOT/\$$PDK/libs.tech/klayout/tech/drc/run_drc.py --path=$$b.gds --topcell=$$b --run_dir=drc --no_density" > drc.log 2>&1); then e=0; else e=$$?; fi; echo "run_drc exit $$e" >> $$d/drc.log; \
	  if (cd $$d && $(RUN) bash -c "python3 \$$PDK_ROOT/\$$PDK/libs.tech/klayout/tech/lvs/run_lvs.py --layout=$$b.gds --netlist=$$b.cdl --topcell=$$b --run_dir=lvs --combine_devices --disable_tap_extraction" > lvs.log 2>&1); then e=0; else e=$$?; fi; echo "run_lvs exit $$e" >> $$d/lvs.log; \
	  if [ $$b = bandgap ]; then n=$(NAMES_bandgap); else n=; fi; if $(RUN) klayout -b -rd path=$$d/lvs/$$b.lvsdb -rd names=$$n -r $(ROOT)/helpers/lvs_names.py >> $$d/lvs.log 2>&1; then e=0; else e=$$?; fi; echo "lvs_names exit $$e" >> $$d/lvs.log; \
	  cp $$d/drc.log results/layout_drc_$$b.log; cp $$d/lvs.log results/layout_lvs_$$b.log; cp $$d/lvs/$${b}_extracted.cir results/layout_extracted_$$b.cir; cp build/layout/generate_$$b.log results/layout_generate_$$b.log; \
	  if grep -q "DRC Check Passed" results/layout_drc_$$b.log && grep -qx "run_drc exit 0" results/layout_drc_$$b.log; then c=0; else c=1; fi; $(SAVE) layout_drc_$$b $$c results/layout_drc_$$b.log results/layout_generate_$$b.log; \
	  if grep -q "PASS (netlists match)" results/layout_lvs_$$b.log && grep -qx "run_lvs exit 0" results/layout_lvs_$$b.log && grep -qx "lvs_names exit 0" results/layout_lvs_$$b.log; then c=0; else c=1; fi; $(SAVE) layout_lvs_$$b $$c results/layout_lvs_$$b.log results/layout_extracted_$$b.cir; done

build/layout/%_pex.spice: build/layout/%.gds layout/extract_%.tcl
	cd build/layout && $(RUN) bash -c 'magic -dnull -noconsole -rcfile $$PDK_ROOT/$$PDK/libs.tech/magic/ihp-sg13g2.magicrc ../../layout/extract_$*.tcl' > extract_$*.log 2>&1

build/layout/bandgap_post.cir: build/layout/bandgap_pex.spice build/layout/bandgap.cdl
	sed '/^.ends$$/d' build/layout/bandgap_pex.spice > $@
	grep '^Q' build/layout/bandgap.cdl | sed 's/^Q/XQ/' >> $@
	printf '.ends\n.subckt bandgap vref vg vdd vss trim3 trim2 trim1 trim0\nX1 %s bandgap_pex\n.ends\n' "$$(sed -n 's/^.subckt bandgap_pex //p' build/layout/bandgap_pex.spice)" >> $@
	[ $$(grep -c '^XQ' $@) -eq 3 ]

build/layout/ldo_post.cir: build/layout/ldo_pex.spice
	cat $< > $@
	printf '.subckt ldo vout fb vref vg vdd vss\nX1 %s ldo_pex\n.ends\n' "$$(sed -n 's/^.subckt ldo_pex //p' $<)" >> $@

build/post_layout/dc_%/dc.txt: tests/dc.cir design/bandgap_sizes.inc build/layout/bandgap_post.cir
	mkdir -p $(@D)
	cp tests/dc.cir design/bandgap_sizes.inc $(@D)
	cp build/layout/bandgap_post.cir $(@D)/bandgap.cir
	$(call corner,$(word 1,$(subst _, ,$*)),27,$(VOLT_$(word 2,$(subst _, ,$*)))) > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b dc.cir > dc.log 2>&1

build/post_layout/ldo_%/result.txt: $(LDO_TESTS) design/bandgap_sizes.inc design/ldo_sizes.inc build/layout/bandgap_post.cir build/layout/ldo_post.cir
	mkdir -p $(@D)
	cp $(LDO_TESTS) design/bandgap_sizes.inc design/ldo_sizes.inc $(@D)
	cp build/layout/bandgap_post.cir $(@D)/bandgap.cir; cp build/layout/ldo_post.cir $(@D)/ldo.cir
	p=$$(echo $* | cut -d_ -f1); v=$$(echo $* | cut -d_ -f2 | tr v .); t=$$(echo $* | cut -d_ -f3 | sed 's/m/-/'); \
	  q=typ; case $$p in ss) q=wcs;; ff) q=bcs;; esac; \
	  printf '.lib cornerMOShv.lib mos_%s\n.lib cornerHBT.lib hbt_%s\n.lib cornerRES.lib res_%s\n.lib cornerCAP.lib cap_%s\n.temp %s\n.param vsupply=%s\n.param mm=0\n' $$p $$q $$q $$q $$t $$v > $(@D)/corner.inc
	cd $(@D) && echo ".param ramp=10n" > ramp.inc && $(RUN) ngspice -b ldo_dc.cir > ldo_dc.log 2>&1 && $(RUN) ngspice -b ldo_psrr.cir > ldo_psrr.log 2>&1 && $(RUN) ngspice -b ldo_startup.cir > ldo_startup.log 2>&1; \
	  for s in 0p5m 2m; do echo ".param istep=$$(echo $$s | tr p .)" > step.inc; $(RUN) ngspice -b ldo_step.cir > step_$$s.log 2>&1; sed "s/^step /step_$$s /" step.txt > step_$$s.txt; done; \
	  for l in 0 250u 1m 2m; do echo ".param iload=$$l" > load.inc; $(RUN) ngspice -b loop.cir > loop_$$l.log 2>&1; sed "s/^loop /loop_$$l /" loop.txt > loop_$$l.txt; done; \
	  cat ldo_dc.txt psrr.txt step_0p5m.txt step_2m.txt loop_*.txt ldo_startup.txt > result.txt

post_layout: $(foreach c,$(POST_BG),build/post_layout/dc_$(c)/dc.txt) $(foreach c,$(POST_LDO),build/post_layout/ldo_$(c)/result.txt)
	mkdir -p results
	cp build/layout/bandgap_post.cir results/bandgap_post.cir; cp build/layout/ldo_post.cir results/ldo_post.cir
	for c in $(POST_BG); do cp build/post_layout/dc_$$c/dc.txt results/pexdc_$$c.txt; done
	for c in $(POST_LDO); do cp build/post_layout/ldo_$$c/result.txt results/pexldo_$$c.txt; done
	if { $(PY) $(ROOT)/helpers/bandgap_results.py corners $(foreach c,$(POST_BG),results/pexdc_$(c).txt) && \
	  $(PY) $(ROOT)/helpers/ldo_results.py corners $(foreach c,$(POST_LDO),results/pexldo_$(c).txt); } > results/post_layout.log 2>&1; then c=0; else c=$$?; fi; \
	  $(SAVE) post_layout $$c results/post_layout.log results/pexdc_*.txt results/pexldo_*.txt results/bandgap_post.cir results/ldo_post.cir

.PHONY: all pnp corners mc startup ldo_model ldo bleed_study ldo_mc broken layout post_layout
.DELETE_ON_ERROR:
.SECONDARY:
