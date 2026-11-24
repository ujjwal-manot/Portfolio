# bandgap_ldo commands: make pnp | pnp_mismatch | corners | mc | startup | ldo_model | ldo | ldo_gear_check | trim_ends | bleed_study | ldo_mc | heads | em | broken | layout | pex_check | post_layout | models | adc_load ADC_INC=file | all
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
ROOT := $(shell git rev-parse --show-toplevel)
RUN := $(ROOT)/setup/run.sh
PY := $(RUN) env PYTHONPATH=$(ROOT)/helpers python3
SAVE := $(RUN) python3 $(ROOT)/helpers/save_result.py results/summary.json
LOGCHECK := $(PY) $(ROOT)/helpers/spice_log_check.py
SPICE := $(ROOT)/helpers/ngspice.sh
CHECKS := $(PY) $(ROOT)/helpers/bandgap_ldo_checks.py
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
MC := $(foreach n,$(shell seq 1 300),build/mc/$(n)/dc.txt)
LDO := design/ldo.cir design/ldo_sizes.inc
LDO_TESTS := tests/ldo_dc.cir tests/ldo_psrr.cir tests/ldo_step.cir tests/ldo_startup.cir tests/loop.cir
LDO_CORNERS := tt_3v3_27 $(foreach p,$(PROCESS),$(foreach v,3v0 3v6,$(foreach t,m40 125,$(p)_$(v)_$(t))))
LDO_RESULTS := $(foreach c,$(LDO_CORNERS),build/ldo/$(c)/result.txt)
LDO_LOGS := ldo_dc ldo_psrr ldo_startup step_0p5m step_2m loop_0 loop_250u loop_1m loop_2m
STARTUP := $(foreach r,$(RAMPS),$(foreach c,$(PROCESS) tt_m40 tt_125,build/startup/$(c)_$(r)/startup.txt))
LDO_MC := $(foreach k,ss ff,$(foreach n,$(shell seq 1 50),build/ldo_mc/$(k)_$(n)/mc.txt))
STUDY_CORNERS := tt_3v3_27 ff_3v6_125 ss_3v0_125
GEAR_CORNERS := tt_3v3_27 ss_3v0_125 ff_3v0_m40
TRIM_CORNERS := tt_3v3_27 ss_3v0_125 ff_3v6_m40
TRIM_RUNS := $(foreach c,$(TRIM_CORNERS),$(foreach k,0 15,build/trim_ends/$(c)_code$(k)/ldo_startup.txt))
LOAD_CORNERS := tt_3v3_27 ss_3v0_125 ff_3v6_m40
EM_RUNS := $(foreach c,$(LDO_CORNERS),build/em/$(c)/em.txt)
BLOCKS := bandgap ldo
NAMES_bandgap := a,e8,e3
POST_BG := tt_3v3 ss_3v0 ff_3v6
POST_LDO := tt_3v3_27 ss_3v0_125 ff_3v6_m40

all: pnp pnp_mismatch corners mc startup ldo_model ldo ldo_gear_check trim_ends bleed_study ldo_mc heads em broken layout pex_check post_layout models $(if $(ADC_INC),adc_load)

corner = printf '.lib cornerMOShv.lib mos_%s\n.lib cornerHBT.lib hbt_%s\n.lib cornerRES.lib res_%s\n.lib cornerCAP.lib cap_%s\n.temp %s\n.param vsupply=%s\n.param mm=0\n' $(1) $(PASSIVE_$(1)) $(PASSIVE_$(1)) $(PASSIVE_$(1)) $(2) $(3)
ldo_corner = p=$$(echo $(1) | cut -d_ -f1); v=$$(echo $(1) | cut -d_ -f2 | tr v .); t=$$(echo $(1) | cut -d_ -f3 | sed 's/m/-/'); q=typ; case $$p in ss) q=wcs;; ff) q=bcs;; esac; \
  printf '.lib cornerMOShv.lib mos_%s\n.lib cornerHBT.lib hbt_%s\n.lib cornerRES.lib res_%s\n.lib cornerCAP.lib cap_%s\n.temp %s\n.param vsupply=%s\n.param mm=0\n' $$p $$q $$q $$q $$t $$v
trim = for b in 3 2 1 0; do if [ $$(( ($(1) >> b) & 1 )) = 1 ]; then to=vdd; else to=0; fi; echo "VT$$b t$$b $$to 0"; done
ldo_suite = cd $(@D) && : > failed.txt && echo ".param ramp=10n" > ramp.inc && $(call trim,8) > trim.inc && for b in ldo_dc ldo_psrr ldo_startup; do if ! $(SPICE) $$b.cir $$b.log; then echo "$$b.cir failed" >> failed.txt; fi; done; \
  for s in 0p5m 2m; do echo ".param istep=$$(echo $$s | tr p .)" > step.inc; rm -f step.txt; if ! $(SPICE) ldo_step.cir step_$$s.log; then echo "ldo_step.cir $$s failed" >> failed.txt; fi; sed "s/^step /step_$$s /" step.txt > step_$$s.txt; done; \
  for l in 0 250u 1m 2m; do echo ".param iload=$$l" > load.inc; rm -f loop.txt; if ! $(SPICE) loop.cir loop_$$l.log; then echo "loop.cir $$l failed" >> failed.txt; fi; sed "s/^loop /loop_$$l /" loop.txt > loop_$$l.txt; done; \
  cat ldo_dc.txt psrr.txt step_0p5m.txt step_2m.txt loop_*.txt ldo_startup.txt > result.txt
ldo_logs = $(foreach d,$(1),$(foreach l,$(LDO_LOGS),$(d)/$(l).log))
failed = if grep -qs . $(addsuffix /failed.txt,$(1)); then c=1; grep -Hs . $(addsuffix /failed.txt,$(1)) >> $(2); fi

pnp:
	mkdir -p build/pnp results
	cp tests/pnp.cir build/pnp
	if (cd build/pnp && $(SPICE) pnp.cir pnp.log); then e=0; else e=1; fi; cp build/pnp/pnp.txt results/pnp.txt; \
	  if $(LOGCHECK) build/pnp/pnp.log > results/pnp.log 2>&1 && [ $$e = 0 ] && ! grep -qi nan results/pnp.txt; then c=0; else c=1; fi; $(SAVE) pnp $$c results/pnp.txt results/pnp.log

pnp_mismatch: tests/pnp_mismatch.sh
	mkdir -p results
	if $(RUN) bash tests/pnp_mismatch.sh > results/pnp_mismatch.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) pnp_mismatch $$c results/pnp_mismatch.log

corners: $(CORNERS)
	mkdir -p results
	for f in $(CORNERS); do cp $$f results/dc_$$(basename $$(dirname $$f)).txt; done
	if $(PY) $(ROOT)/helpers/bandgap_results.py corners results/dc_*_*.txt > results/corners.log 2>&1; then c=0; else c=1; fi; \
	  if ! $(LOGCHECK) $(CORNERS:.txt=.log) >> results/corners.log 2>&1; then c=1; fi; $(call failed,$(patsubst %/,%,$(dir $(CORNERS))),results/corners.log); $(SAVE) corners $$c results/corners.log results/dc_*_*.txt

mc: $(MC)
	mkdir -p results
	rm -f results/mc_*.txt
	for f in $(MC); do cp $$f results/mc_$$(basename $$(dirname $$f)).txt; done
	if $(PY) $(ROOT)/helpers/bandgap_results.py mc results/mc_*.txt > results/mc.log 2>&1; then c=0; else c=1; fi; \
	  { echo "corner.inc of the runs, seed line left out, each line with the number of runs that used it:"; sed '/seed/d' $(MC:dc.txt=corner.inc) | sort | uniq -c; } >> results/mc.log; \
	  if ! $(LOGCHECK) $(MC:.txt=.log) >> results/mc.log 2>&1; then c=1; fi; $(call failed,$(patsubst %/,%,$(dir $(MC))),results/mc.log); $(SAVE) mc $$c results/mc.log results/mc_*.txt

startup: $(STARTUP)
	mkdir -p results
	for f in $(STARTUP); do cp $$f results/startup_$$(basename $$(dirname $$f)).txt; done
	if $(PY) $(ROOT)/helpers/bandgap_results.py startup results/startup_*.txt > results/startup.log 2>&1; then c=0; else c=1; fi; \
	  if ! $(LOGCHECK) $(STARTUP:.txt=.log) >> results/startup.log 2>&1; then c=1; fi; $(call failed,$(patsubst %/,%,$(dir $(STARTUP))),results/startup.log); $(SAVE) startup $$c results/startup.log results/startup_*.txt

build/corners/%/dc.txt: tests/dc.cir $(BANDGAP)
	mkdir -p $(@D)
	cp $^ $(@D)
	$(call corner,$(word 1,$(subst _, ,$*)),27,$(VOLT_$(word 2,$(subst _, ,$*)))) > $(@D)/corner.inc
	cd $(@D) && : > failed.txt && if ! $(SPICE) dc.cir dc.log; then echo "dc.cir failed" >> failed.txt; fi

build/mc/%/dc.txt: tests/dc.cir $(BANDGAP)
	mkdir -p $(@D)
	cp $^ $(@D)
	printf '.lib cornerMOShv.lib mos_tt_mismatch\n.lib cornerHBT.lib hbt_typ_mismatch\n.lib cornerRES.lib res_typ_mismatch\n.lib cornerCAP.lib cap_typ_mismatch\n.temp 27\n.param vsupply=3.3\n.param mm=1\n.option seed=%s\n' $* > $(@D)/corner.inc
	cd $(@D) && : > failed.txt && if ! $(SPICE) dc.cir dc.log; then echo "dc.cir failed" >> failed.txt; fi

build/startup/%/startup.txt: tests/startup.cir $(BANDGAP)
	mkdir -p $(@D)
	cp $^ $(@D)
	n=$*; ramp=$${n##*_}; c=$${n%_*}; p=$${c%%_*}; t=27; case $$c in *_m40) t=-40;; *_125) t=125;; esac; \
	  q=typ; case $$p in ss) q=wcs;; ff) q=bcs;; esac; \
	  printf '.lib cornerMOShv.lib mos_%s\n.lib cornerHBT.lib hbt_%s\n.lib cornerRES.lib res_%s\n.lib cornerCAP.lib cap_%s\n.temp %s\n.param vsupply=3.3\n.param mm=0\n' $$p $$q $$q $$q $$t > $(@D)/corner.inc; \
	  echo ".param ramp=$$ramp" > $(@D)/ramp.inc
	cd $(@D) && : > failed.txt && if ! $(SPICE) startup.cir startup.log; then echo "startup.cir failed" >> failed.txt; fi

ldo_model: tests/loop.cir tests/tian_model.cir $(BANDGAP)
	mkdir -p build/ldo_model results
	cp tests/loop.cir $(BANDGAP) design/ldo_sizes.inc build/ldo_model
	cp tests/tian_model.cir build/ldo_model/ldo.cir
	$(call corner,tt,27,3.3) > build/ldo_model/corner.inc
	echo ".param iload=0" > build/ldo_model/load.inc
	cd build/ldo_model && : > failed.txt && if ! $(SPICE) loop.cir loop.log; then echo "loop.cir failed" >> failed.txt; fi
	cp build/ldo_model/loop.txt results/ldo_model.txt
	if $(PY) $(ROOT)/helpers/ldo_results.py model results/ldo_model.txt > results/ldo_model.log 2>&1; then c=0; else c=1; fi; \
	  if ! $(LOGCHECK) build/ldo_model/loop.log >> results/ldo_model.log 2>&1; then c=1; fi; $(call failed,build/ldo_model,results/ldo_model.log); $(SAVE) ldo_model $$c results/ldo_model.log results/ldo_model.txt

ldo: $(LDO_RESULTS)
	mkdir -p results
	for c in $(LDO_CORNERS); do cp build/ldo/$$c/result.txt results/ldo_$$c.txt; done
	if $(PY) $(ROOT)/helpers/ldo_results.py corners $(foreach c,$(LDO_CORNERS),results/ldo_$(c).txt) > results/ldo.log 2>&1; then c=0; else c=1; fi; \
	  if ! $(LOGCHECK) $(call ldo_logs,$(foreach c,$(LDO_CORNERS),build/ldo/$(c))) >> results/ldo.log 2>&1; then c=1; fi; $(call failed,$(foreach c,$(LDO_CORNERS),build/ldo/$(c)),results/ldo.log); $(SAVE) ldo $$c results/ldo.log $(foreach c,$(LDO_CORNERS),results/ldo_$(c).txt)

build/ldo/%/result.txt: $(LDO_TESTS) $(BANDGAP) $(LDO)
	mkdir -p $(@D)
	cp $^ $(@D)
	$(call ldo_corner,$*) > $(@D)/corner.inc
	$(ldo_suite)

ldo_gear_check: $(foreach c,$(GEAR_CORNERS),build/ldo/$(c)/result.txt)
	mkdir -p results
	g=0; for c in $(GEAR_CORNERS); do d=build/gear_check/$$c; mkdir -p $$d; cp build/ldo/$$c/*.cir build/ldo/$$c/*.inc $$d; \
	  sed -i '/^\.option method=gear$$/d; s/^\(\.tran .*\)$$/\1 0 1n/' $$d/ldo_startup.cir; \
	  : > $$d/failed.txt; if ! (cd $$d && $(SPICE) ldo_startup.cir ldo_startup.log); then echo "ldo_startup.cir failed" >> $$d/failed.txt; fi; if [ -s $$d/failed.txt ]; then g=1; fi; \
	  cp build/ldo/$$c/ldo_startup.txt results/gear_check_$${c}_gear.txt; cp $$d/ldo_startup.txt results/gear_check_$${c}_trap.txt; done; \
	c=$$g; : > results/ldo_gear_check.log; for k in $(GEAR_CORNERS); do echo "$$k: the bench (Gear) against the trapezoidal rule held to a 1 ns step" >> results/ldo_gear_check.log; \
	  if ! $(PY) $(ROOT)/helpers/same_values.py final_v=1e-3,top_v=1e-3,settle_s=2e-6 results/gear_check_$${k}_gear.txt results/gear_check_$${k}_trap.txt >> results/ldo_gear_check.log 2>&1; then c=1; fi; done; \
	  if ! $(LOGCHECK) $(foreach c,$(GEAR_CORNERS),build/ldo/$(c)/ldo_startup.log build/gear_check/$(c)/ldo_startup.log) >> results/ldo_gear_check.log 2>&1; then c=1; fi; \
	  $(call failed,$(foreach c,$(GEAR_CORNERS),build/ldo/$(c) build/gear_check/$(c)),results/ldo_gear_check.log); $(SAVE) ldo_gear_check $$c results/ldo_gear_check.log results/gear_check_*.txt

build/trim_ends/%/ldo_startup.txt: tests/ldo_startup.cir $(BANDGAP) $(LDO)
	mkdir -p $(@D)
	cp $^ $(@D)
	n=$*; c=$${n%_code*}; k=$${n##*_code}; $(call ldo_corner,$$c) > $(@D)/corner.inc; $(call trim,$$k) > $(@D)/trim.inc
	cd $(@D) && : > failed.txt && echo ".param ramp=10n" > ramp.inc && if ! $(SPICE) ldo_startup.cir ldo_startup.log; then echo "ldo_startup.cir failed" >> failed.txt; fi

trim_ends: $(TRIM_RUNS)
	mkdir -p results
	for f in $(TRIM_RUNS); do cp $$f results/trim_ends_$$(basename $$(dirname $$f)).txt; done
	if $(CHECKS) startup $(foreach f,$(TRIM_RUNS),results/trim_ends_$(notdir $(patsubst %/,%,$(dir $(f)))).txt) > results/trim_ends.log 2>&1; then c=0; else c=1; fi; \
	  if ! $(LOGCHECK) $(TRIM_RUNS:.txt=.log) >> results/trim_ends.log 2>&1; then c=1; fi; $(call failed,$(patsubst %/,%,$(dir $(TRIM_RUNS))),results/trim_ends.log); $(SAVE) trim_ends $$c results/trim_ends.log results/trim_ends_*.txt

bleed_study: ldo
	mkdir -p build/study results
	cp -r design tests Makefile build/study
	patch -s -F0 -d build/study -p1 < study/resistor_bleed.patch
	$(MAKE) -C build/study $(foreach c,$(STUDY_CORNERS),build/ldo/$(c)/result.txt) > build/study/make.log 2>&1
	for c in $(STUDY_CORNERS); do cp build/study/build/ldo/$$c/result.txt results/bleed_study_$$c.txt; done
	if $(PY) $(ROOT)/helpers/ldo_results.py study $(foreach c,$(STUDY_CORNERS),results/ldo_$(c).txt) $(foreach c,$(STUDY_CORNERS),results/bleed_study_$(c).txt) > results/bleed_study.log 2>&1; then c=0; else c=1; fi; \
	  if ! $(LOGCHECK) $(call ldo_logs,$(foreach c,$(STUDY_CORNERS),build/study/build/ldo/$(c))) >> results/bleed_study.log 2>&1; then c=1; fi; $(call failed,$(foreach c,$(STUDY_CORNERS),build/study/build/ldo/$(c)),results/bleed_study.log); $(SAVE) bleed_study $$c results/bleed_study.log results/bleed_study_*.txt

build/ldo_mc/%/mc.txt: tests/ldo_mc.cir $(BANDGAP) $(LDO)
	mkdir -p $(@D)
	cp $^ $(@D)
	k=$$(echo $* | cut -d_ -f1); n=$$(echo $* | cut -d_ -f2); q=wcs; v=3.0; if [ $$k = ff ]; then q=bcs; v=3.6; fi; \
	  printf '.lib cornerMOShv.lib mos_%s_mismatch\n.lib cornerHBT.lib hbt_%s_mismatch\n.lib cornerRES.lib res_%s_mismatch\n.lib cornerCAP.lib cap_%s_mismatch\n.temp 125\n.param vsupply=%s\n.param mm=1\n.option seed=%s\n' $$k $$q $$q $$q $$v $$n > $(@D)/corner.inc
	cd $(@D) && : > failed.txt && if ! $(SPICE) ldo_mc.cir mc.log; then echo "ldo_mc.cir failed" >> failed.txt; fi

ldo_mc: $(LDO_MC)
	mkdir -p results
	for f in $(LDO_MC); do cp $$f results/ldo_mc_$$(basename $$(dirname $$f)).txt; done
	f=0; for k in ss ff; do if $(PY) $(ROOT)/helpers/ldo_results.py mc $$k results/ldo_mc_$${k}_*.txt > results/ldo_mc_$$k.log 2>&1; then c=0; else c=1; fi; \
	  { echo "corner.inc of the runs, seed line left out, each line with the number of runs that used it:"; sed '/seed/d' build/ldo_mc/$${k}_*/corner.inc | sort | uniq -c; } >> results/ldo_mc_$$k.log; \
	  if ! $(LOGCHECK) build/ldo_mc/$${k}_*/mc.log >> results/ldo_mc_$$k.log 2>&1; then c=1; fi; \
	  if grep -qs . build/ldo_mc/$${k}_*/failed.txt; then c=1; grep -Hs . build/ldo_mc/$${k}_*/failed.txt >> results/ldo_mc_$$k.log; fi; \
	  if ! $(SAVE) ldo_mc_$$k $$c results/ldo_mc_$$k.log results/ldo_mc_$${k}_*.txt; then f=1; fi; done; exit $$f

heads: tests/heads.cir
	mkdir -p build/heads results
	cp tests/heads.cir build/heads
	cd build/heads && : > failed.txt && if ! $(SPICE) heads.cir heads.log; then echo "heads.cir failed" >> failed.txt; fi
	cp build/heads/heads.txt results/heads.txt
	if $(LOGCHECK) build/heads/heads.log > results/heads.log 2>&1 && ! grep -qi nan results/heads.txt; then c=0; else c=1; fi; $(call failed,build/heads,results/heads.log); $(SAVE) heads $$c results/heads.log results/heads.txt

build/em/%/em.txt: tests/em.cir $(BANDGAP) $(LDO) $(ROOT)/helpers/em_check.py
	mkdir -p $(@D)
	cp tests/em.cir $(BANDGAP) $(LDO) $(@D)
	cat design/bandgap_sizes.inc design/ldo_sizes.inc > $(@D)/sizes.inc
	$(call ldo_corner,$*) > $(@D)/corner.inc
	cd $(@D) && $(PY) $(ROOT)/helpers/em_check.py probes sizes.inc bandgap.cir ldo.cir -- x1=bandgap x2=ldo > probes.inc && : > failed.txt && if ! $(SPICE) em.cir em.log; then echo "em.cir failed" >> failed.txt; fi

em: $(EM_RUNS) build/layout/ldo.gds layout/pins.py
	mkdir -p results
	$(RUN) klayout -b -rd gds=build/layout/ldo.gds -r layout/pins.py > results/em_pins.log 2>&1
	own=$$(sed -n 's/^own pins //p' results/em_pins.log); c=0; : > results/em.log; for k in $(LDO_CORNERS); do cp build/em/$$k/em.txt results/em_$$k.txt; echo "$$k, 2 mA load:" >> results/em.log; \
	  if ! $(PY) $(ROOT)/helpers/em_check.py check build/em/$$k/sizes.inc build/em/$$k/bandgap.cir build/em/$$k/ldo.cir -- x1=bandgap x2=ldo $$own results/em_$$k.txt >> results/em.log 2>&1; then c=1; fi; done; \
	  if ! $(LOGCHECK) $(EM_RUNS:.txt=.log) >> results/em.log 2>&1; then c=1; fi; $(call failed,$(patsubst %/,%,$(dir $(EM_RUNS))),results/em.log); $(SAVE) em $$c results/em.log results/em_pins.log results/em_*.txt

build/adc_load/%/load.txt: tests/ldo_load.cir $(BANDGAP) $(LDO) $(ADC_INC) $(ROOT)/projects/opamp/results/corners.log
	mkdir -p $(@D)
	cp tests/ldo_load.cir $(BANDGAP) $(LDO) $(@D)
	cp $(ADC_INC) $(@D)/adc.inc
	$(call ldo_corner,$*) > $(@D)/corner.inc
	echo ".param iopamp=$$(sed -n 's/^supply_a *worst \([^ ]*\) .*/\1/p' $(ROOT)/projects/opamp/results/corners.log)" > $(@D)/load.inc
	cd $(@D) && : > failed.txt && if ! $(SPICE) ldo_load.cir load.log; then echo "ldo_load.cir failed" >> failed.txt; fi

adc_load: $(foreach c,$(LOAD_CORNERS),build/adc_load/$(c)/load.txt)
	mkdir -p results
	for c in $(LOAD_CORNERS); do cp build/adc_load/$$c/load.txt results/adc_load_$$c.txt; done
	if $(CHECKS) load $(foreach c,$(LOAD_CORNERS),results/adc_load_$(c).txt) > results/adc_load.log 2>&1; then c=0; else c=1; fi; \
	  if ! $(LOGCHECK) $(foreach c,$(LOAD_CORNERS),build/adc_load/$(c)/load.log) >> results/adc_load.log 2>&1; then c=1; fi; $(call failed,$(foreach c,$(LOAD_CORNERS),build/adc_load/$(c)),results/adc_load.log); $(SAVE) adc_load $$c results/adc_load.log results/adc_load_*.txt

broken:
	rm -rf build/broken
	mkdir -p results build/broken
	f=0; for p in broken/*.patch; do n=$$(basename $$p .patch); d=build/broken/$$n; mkdir -p $$d; cp -r design tests study layout Makefile $$d; \
	  patch -s -F0 -d $$d -p1 < $$p; want=$$(sed -n '1s/^Expected failure: //p' $$p); run=$$(sed -n '2s/^Run: //p' $$p); \
	  log=$$(sed -n '3s/^Log: //p' $$p); [ -n "$$log" ] || log=results/$${run%% *}.log; \
	  if $(MAKE) -C $$d $$run > $$d/make.log 2>&1; then c=1; elif [ -n "$$want" ] && grep -qF -- "$$want" $$d/$$log; then c=0; else c=2; fi; \
	  cp $$d/$$log results/broken_$$n.log; if ! $(SAVE) broken_$$n $$c results/broken_$$n.log; then f=1; fi; done; exit $$f

build/layout/%.cdl: design/%.cir $(BANDGAP) $(LDO) $(ROOT)/helpers/spice_flatten.py
	mkdir -p build/layout
	cat design/bandgap_sizes.inc design/ldo_sizes.inc > build/layout/sizes.inc
	python3 $(ROOT)/helpers/spice_flatten.py $* build/layout/sizes.inc $< > $@

build/layout/%.gds: build/layout/%.cdl layout/%.py $(ROOT)/helpers/hv_layout.py $(ROOT)/helpers/row_layout.py
	$(RUN) env HELPERS=$(ROOT)/helpers NETLIST=build/layout/$*.cdl OUT=build/layout klayout -b -r layout/$*.py > build/layout/generate_$*.log 2>&1

layout: $(foreach b,$(BLOCKS),build/layout/$(b).gds build/layout/$(b).cdl)
	rm -rf build/layout/checks
	mkdir -p results build/layout/checks
	f=0; for b in $(BLOCKS); do d=build/layout/checks/$$b; mkdir -p $$d; cp build/layout/$$b.gds build/layout/$$b.cdl $$d; \
	  if (cd $$d && $(RUN) bash -c "python3 \$$PDK_ROOT/\$$PDK/libs.tech/klayout/tech/drc/run_drc.py --path=$$b.gds --topcell=$$b --run_dir=drc --no_density" > drc.log 2>&1); then e=0; else e=$$?; fi; echo "run_drc exit $$e" >> $$d/drc.log; \
	  if (cd $$d && $(RUN) bash -c "python3 \$$PDK_ROOT/\$$PDK/libs.tech/klayout/tech/lvs/run_lvs.py --layout=$$b.gds --netlist=$$b.cdl --topcell=$$b --run_dir=lvs --combine_devices --disable_tap_extraction" > lvs.log 2>&1); then e=0; else e=$$?; fi; echo "run_lvs exit $$e" >> $$d/lvs.log; \
	  if [ $$b = bandgap ]; then n=$(NAMES_bandgap); else n=; fi; if $(RUN) klayout -b -rd path=$$d/lvs/$$b.lvsdb -rd names=$$n -r $(ROOT)/helpers/lvs_names.py >> $$d/lvs.log 2>&1; then e=0; else e=$$?; fi; echo "lvs_names exit $$e" >> $$d/lvs.log; \
	  cp $$d/drc.log results/layout_drc_$$b.log; cp $$d/lvs.log results/layout_lvs_$$b.log; cp $$d/lvs/$${b}_extracted.cir results/layout_extracted_$$b.cir; cp build/layout/generate_$$b.log results/layout_generate_$$b.log; \
	  if grep -q "DRC Check Passed" results/layout_drc_$$b.log && grep -qx "run_drc exit 0" results/layout_drc_$$b.log; then c=0; else c=1; fi; if ! $(SAVE) layout_drc_$$b $$c results/layout_drc_$$b.log results/layout_generate_$$b.log; then f=1; fi; \
	  if grep -q "PASS (netlists match)" results/layout_lvs_$$b.log && grep -qx "run_lvs exit 0" results/layout_lvs_$$b.log && grep -qx "lvs_names exit 0" results/layout_lvs_$$b.log; then c=0; else c=1; fi; if ! $(SAVE) layout_lvs_$$b $$c results/layout_lvs_$$b.log results/layout_extracted_$$b.cir; then f=1; fi; done; exit $$f

build/layout/%_pex.spice: build/layout/%.gds layout/extract_%.tcl
	cd build/layout && $(RUN) bash -c 'magic -dnull -noconsole -rcfile $$PDK_ROOT/$$PDK/libs.tech/magic/ihp-sg13g2.magicrc ../../layout/extract_$*.tcl' > extract_$*.log 2>&1

build/layout/bandgap_post.cir: build/layout/bandgap_pex.spice build/layout/bandgap.cdl $(ROOT)/helpers/bandgap_ldo_checks.py
	$(CHECKS) clean build/layout/bandgap_pex.spice 2> build/layout/bandgap_dropped.txt | sed '/^.ends$$/d' > $@
	grep '^Q' build/layout/bandgap.cdl | sed 's/^Q/XQ/' >> $@
	printf '.ends\n.subckt bandgap vref vg vdd vss trim3 trim2 trim1 trim0\nX1 %s bandgap_pex\n.ends\n' "$$(sed -n 's/^.subckt bandgap_pex //p' build/layout/bandgap_pex.spice)" >> $@
	[ $$(grep -c '^XQ' $@) -eq 3 ]

build/layout/ldo_post.cir: build/layout/ldo_pex.spice $(ROOT)/helpers/bandgap_ldo_checks.py
	$(CHECKS) clean $< 2> build/layout/ldo_dropped.txt > $@
	printf '.subckt ldo vout fb vref vg vdd vss\nX1 %s ldo_pex\n.ends\n' "$$(sed -n 's/^.subckt ldo_pex //p' $<)" >> $@

pex_check: build/layout/bandgap_post.cir build/layout/ldo_post.cir
	mkdir -p results
	if $(CHECKS) pex build/layout/bandgap_post.cir build/layout/ldo_post.cir > results/pex_check.log 2>&1; then c=0; else c=1; fi; \
	  { echo "lines left out of the post-layout netlists (bandgap, then ldo):"; cat build/layout/bandgap_dropped.txt build/layout/ldo_dropped.txt; \
	    echo "element lines by first letter in the extracted netlists (bandgap, then ldo):"; for b in $(BLOCKS); do grep -v '^[*.+]' build/layout/$${b}_pex.spice | cut -c1 | sort | uniq -c; done; } >> results/pex_check.log; \
	  $(SAVE) pex_check $$c results/pex_check.log

build/post_layout/dc_%/dc.txt: tests/dc.cir design/bandgap_sizes.inc build/layout/bandgap_post.cir
	mkdir -p $(@D)
	cp tests/dc.cir design/bandgap_sizes.inc $(@D)
	cp build/layout/bandgap_post.cir $(@D)/bandgap.cir
	$(call corner,$(word 1,$(subst _, ,$*)),27,$(VOLT_$(word 2,$(subst _, ,$*)))) > $(@D)/corner.inc
	cd $(@D) && : > failed.txt && if ! $(SPICE) dc.cir dc.log; then echo "dc.cir failed" >> failed.txt; fi

build/post_layout/ldo_%/result.txt: $(LDO_TESTS) design/bandgap_sizes.inc design/ldo_sizes.inc build/layout/bandgap_post.cir build/layout/ldo_post.cir
	mkdir -p $(@D)
	cp $(LDO_TESTS) design/bandgap_sizes.inc design/ldo_sizes.inc $(@D)
	cp build/layout/bandgap_post.cir $(@D)/bandgap.cir; cp build/layout/ldo_post.cir $(@D)/ldo.cir
	$(call ldo_corner,$*) > $(@D)/corner.inc
	$(ldo_suite)

post_layout: $(foreach c,$(POST_BG),build/post_layout/dc_$(c)/dc.txt) $(foreach c,$(POST_LDO),build/post_layout/ldo_$(c)/result.txt) $(foreach c,$(POST_BG),build/corners/$(c)/dc.txt)
	mkdir -p results
	cp build/layout/bandgap_post.cir results/bandgap_post.cir; cp build/layout/ldo_post.cir results/ldo_post.cir
	for c in $(POST_BG); do cp build/post_layout/dc_$$c/dc.txt results/pexdc_$$c.txt; done
	for c in $(POST_LDO); do cp build/post_layout/ldo_$$c/result.txt results/pexldo_$$c.txt; done
	if { $(PY) $(ROOT)/helpers/bandgap_results.py corners $(foreach c,$(POST_BG),results/pexdc_$(c).txt) && \
	  $(PY) $(ROOT)/helpers/ldo_results.py corners $(foreach c,$(POST_LDO),results/pexldo_$(c).txt); } > results/post_layout.log 2>&1; then c=0; else c=1; fi; \
	  for k in $(POST_BG); do echo "$$k: post-layout bandgap at code 8, before trim, against the schematic (allowed shift: seven trim steps, the room above code 8)" >> results/post_layout.log; \
	    if ! $(PY) $(ROOT)/helpers/same_values.py untrimmed_v=0.0218 results/dc_$$k.txt results/pexdc_$$k.txt >> results/post_layout.log 2>&1; then c=1; fi; done; \
	  if ! $(LOGCHECK) $(foreach c,$(POST_BG),build/post_layout/dc_$(c)/dc.log) $(call ldo_logs,$(foreach c,$(POST_LDO),build/post_layout/ldo_$(c))) >> results/post_layout.log 2>&1; then c=1; fi; \
	  $(call failed,$(foreach c,$(POST_BG),build/post_layout/dc_$(c)) $(foreach c,$(POST_LDO),build/post_layout/ldo_$(c)),results/post_layout.log); $(SAVE) post_layout $$c results/post_layout.log results/pexdc_*.txt results/pexldo_*.txt results/bandgap_post.cir results/ldo_post.cir

MODEL := design/bandgap_model.cir design/ldo_model.cir
MODEL_BG := $(foreach c,$(CORNERS:build/corners/%/dc.txt=%),build/model/dc_$(c)/dc.txt)
MODEL_SU := $(foreach c,$(STARTUP:build/startup/%/startup.txt=%),build/model/startup_$(c)/startup.txt)
MODEL_LDO := $(foreach c,$(LDO_CORNERS),build/model/ldo_$(c)/result.txt)
BG_TOL := vref_v=3e-3,untrimmed_v=5e-3,tc_ppm_per_c=10,supply_a=10e-6,line_v_per_v=1e-3,step_v=3e-4,code=2
SU_TOL := final_v=5e-3,settle_s=20e-6
LDO_TOL := ldo_dc.vout_v=5e-3,ldo_dc.load_reg_v=2e-3,ldo_dc.iq_a=40e-6,step_0p5m.dip_v=15e-3,step_2m.peak_v=15e-3,loop_0.pm_deg=10,loop_2m.pm_deg=15,ldo_startup.final_v=5e-3,ldo_startup.top_v=15e-3
model_files = cp design/bandgap_model.cir $(@D)/bandgap.cir; cp design/ldo_model.cir $(@D)/ldo.cir; cp build/model/model_params.inc $(@D)/bandgap_sizes.inc; echo "* the model's parameters are all in bandgap_sizes.inc" > $(@D)/ldo_sizes.inc
flat = awk '{for (i = 2; i < NF; i += 2) print "v", $$1 "." $$i, $$(i + 1)}' $(1) > $(2)

build/model/fit/model_fit.txt: tests/model_fit.cir $(BANDGAP) $(LDO)
	mkdir -p $(@D)
	cp $^ $(@D)
	$(call corner,tt,27,3.3) > $(@D)/corner.inc
	cd $(@D) && : > failed.txt && if ! $(SPICE) model_fit.cir model_fit.log; then echo "model_fit.cir failed" >> failed.txt; fi
	cd $(@D) && awk '{print "curve temp_c", $$1, "vref_v", $$2}' model_curve.txt >> model_fit.txt && echo "zero is real: temp_c (the 0 C point of the vref curve)" >> model_fit.txt

build/model/model_params.inc: build/model/fit/model_fit.txt build/corners/tt_3v3/dc.txt build/ldo/tt_3v3_27/result.txt build/startup/tt_10n/startup.txt build/startup/tt_1m/startup.txt build/em/tt_3v3_27/em.txt $(ROOT)/helpers/bandgap_ldo_model.py
	$(PY) $(ROOT)/helpers/bandgap_ldo_model.py $(filter-out %.py,$^) > $@

build/model/dc_%/dc.txt: tests/dc.cir $(MODEL) build/model/model_params.inc
	mkdir -p $(@D)
	cp tests/dc.cir $(@D); $(model_files)
	$(call corner,$(word 1,$(subst _, ,$*)),27,$(VOLT_$(word 2,$(subst _, ,$*)))) > $(@D)/corner.inc
	cd $(@D) && : > failed.txt && if ! $(SPICE) dc.cir dc.log; then echo "dc.cir failed" >> failed.txt; fi

build/model/startup_%/startup.txt: tests/startup.cir $(MODEL) build/model/model_params.inc build/startup/%/startup.txt
	mkdir -p $(@D)
	cp tests/startup.cir build/startup/$*/corner.inc build/startup/$*/ramp.inc $(@D); $(model_files)
	cd $(@D) && : > failed.txt && if ! $(SPICE) startup.cir startup.log; then echo "startup.cir failed" >> failed.txt; fi

build/model/ldo_%/result.txt: $(LDO_TESTS) $(MODEL) build/model/model_params.inc
	mkdir -p $(@D)
	cp $(LDO_TESTS) $(@D); $(model_files)
	$(call ldo_corner,$*) > $(@D)/corner.inc
	$(ldo_suite)

models: $(MODEL_BG) $(MODEL_SU) $(MODEL_LDO) $(CORNERS) $(STARTUP) $(LDO_RESULTS)
	mkdir -p results build/model/compare
	cp build/model/model_params.inc results/model_params.inc; cp build/model/fit/model_fit.txt results/model_fit.txt
	c=0; : > results/models.log; \
	  for k in $(CORNERS:build/corners/%/dc.txt=%); do r=validation; [ $$k = tt_3v3 ] && r=fit; echo "bandgap dc.cir at $$k ($$r), transistor then model:" >> results/models.log; \
	    if ! $(PY) $(ROOT)/helpers/same_values.py $(BG_TOL) build/corners/$$k/dc.txt build/model/dc_$$k/dc.txt >> results/models.log 2>&1; then c=1; fi; done; \
	  for k in $(STARTUP:build/startup/%/startup.txt=%); do r=validation; case $$k in tt_10n|tt_1m) r=fit;; esac; echo "bandgap startup.cir at $$k ($$r), transistor then model:" >> results/models.log; \
	    if ! $(PY) $(ROOT)/helpers/same_values.py $(SU_TOL) build/startup/$$k/startup.txt build/model/startup_$$k/startup.txt >> results/models.log 2>&1; then c=1; fi; done; \
	  for k in $(LDO_CORNERS); do r=validation; [ $$k = tt_3v3_27 ] && r=fit; echo "LDO suite at $$k ($$r), transistor then model:" >> results/models.log; \
	    $(call flat,build/ldo/$$k/result.txt,build/model/compare/ldo_$$k.txt); $(call flat,build/model/ldo_$$k/result.txt,build/model/compare/model_$$k.txt); \
	    if ! $(PY) $(ROOT)/helpers/same_values.py $(LDO_TOL) build/model/compare/ldo_$$k.txt build/model/compare/model_$$k.txt >> results/models.log 2>&1; then c=1; fi; done; \
	  if ! $(LOGCHECK) build/model/fit/model_fit.log $(MODEL_BG:.txt=.log) $(MODEL_SU:.txt=.log) $(call ldo_logs,$(patsubst %/,%,$(dir $(MODEL_LDO)))) >> results/models.log 2>&1; then c=1; fi; \
	  $(call failed,build/model/fit $(patsubst %/,%,$(dir $(MODEL_BG) $(MODEL_SU) $(MODEL_LDO))),results/models.log); \
	  $(SAVE) models $$c results/models.log results/model_params.inc results/model_fit.txt

.PHONY: models all pnp pnp_mismatch corners mc startup ldo_model ldo ldo_gear_check trim_ends bleed_study ldo_mc heads em adc_load broken layout pex_check post_layout
.DELETE_ON_ERROR:
.SECONDARY:
