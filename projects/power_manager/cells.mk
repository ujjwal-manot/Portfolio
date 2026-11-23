# power_manager cell checks: make -f cells.mk cvc | layout | post_layout | cells_broken
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
ROOT := $(shell git rev-parse --show-toplevel)
RUN := $(ROOT)/setup/run.sh
SAVE := $(RUN) python3 $(ROOT)/helpers/save_result.py results/summary.json
FLAT := python3 $(ROOT)/helpers/spice_flatten.py
CHECK := $(RUN) python3 $(ROOT)/helpers/spice_log_check.py
PY := $(RUN) env PYTHONPATH=$(ROOT)/helpers python3
CVC_RUNS := shifter_hv_3v6 shifter_hv_3v3 dldo_unit_3v6 dldo_unit_3v3
CELLS_BROKEN := $(basename $(notdir $(wildcard broken/cells_*.patch)))
LAYOUTS := dldo_unit comparator dldo_array
NAMES_dldo_unit := on,out,vin,vdd,vss
NAMES_comparator := inp,inn,clk,outp,outn,vdd,vss
NAMES_dldo_array := out,vin,vdd,vss,$(shell seq -s, -f 'on%g' 0 127)
UNIT_CORNERS := tt_27_1v2_3v3 $(foreach p,ss ff sf fs,$(foreach t,m40 125,$(foreach v,1v08_3v6 1v32_3v0,$(p)_$(t)_$(v))))
CMP_CORNERS := tt_27_1v2 ss_125_1v08 ss_m40_1v08 ff_m40_1v32 ff_125_1v32 sf_27_1v2 fs_27_1v2
TEMP_27 := 27
TEMP_125 := 125
TEMP_m40 := -40
POST := $(foreach k,sch ext,$(foreach c,$(UNIT_CORNERS),build/post/unit_$(k)_$(c)/unit.txt build/post/array_$(k)_$(c)/array.txt) $(foreach c,$(CMP_CORNERS),build/post/cmp_$(k)_$(c)/cmp.txt))
word_ = $(word $(2),$(subst _, ,$(1)))
lv_corner = printf '.lib cornerMOSlv.lib mos_%s\n.temp %s\n.param vsupply=%s\n.param mm=0\n' $(call word_,$(1),1) $(TEMP_$(call word_,$(1),2)) $(subst v,.,$(call word_,$(1),3))
hv_corner = printf '.lib cornerMOSlv.lib mos_%s\n.lib cornerMOShv.lib mos_%s\n.temp %s\n.param vdd_v=%s vin_v=%s\n' $(call word_,$(1),1) $(call word_,$(1),1) $(TEMP_$(call word_,$(1),2)) $(subst v,.,$(call word_,$(1),3)) $(subst v,.,$(call word_,$(1),4))
wrap = { cat build/layout/$(1)_pex.spice; printf '.subckt $(1) %s\nX1 %s $(1)_pex\n.ends\n' "$$(sed -n 's/^.subckt [^ ]* //p' build/layout/$(1).cdl)" "$$(sed -n '/^.subckt $(1)_pex /,/^[^+.]/p' build/layout/$(1)_pex.spice | sed '$$d' | tr '\n' ' ' | sed 's/^.subckt [^ ]* //; s/ + / /g')"; }
ONS := printf 'XA %s out vin vdd 0 dldo_array\n' "$$(printf 'vdd %.0s' $$(seq 128))"

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

build/layout/unit_sizes.inc: design/dldo_sizes.inc design/shifter_hv_sizes.inc
	mkdir -p $(@D)
	cat $^ > $@

build/layout/dldo_unit.cdl: build/layout/unit_sizes.inc design/shifter_hv.cir design/dldo_unit.cir
	$(FLAT) dldo_unit $^ > $@

build/layout/comparator.cdl: design/comparator_sizes.inc $(ROOT)/projects/adc/design/comparator.cir
	mkdir -p $(@D)
	$(FLAT) comparator $^ > $@

build/layout/dldo_array.cir:
	mkdir -p $(@D)
	{ printf '* Digital LDO switch array of 128 units for LVS and the post-layout runs, written by cells.mk.\n.subckt dldo_array %s out vin vdd vss\n' "$$(seq -s ' ' -f 'on%g' 0 127)"; \
	  for k in $$(seq 0 127); do echo "XU$$k on$$k out vin vdd vss dldo_unit"; done; echo .ends; } > $@

build/layout/dldo_array.cdl: build/layout/unit_sizes.inc design/shifter_hv.cir design/dldo_unit.cir build/layout/dldo_array.cir
	$(FLAT) dldo_array $^ > $@

build/layout/dldo_unit.gds build/layout/dldo_array.gds: build/layout/%.gds: build/layout/dldo_unit.cdl layout/%.py layout/dldo_unit.py $(ROOT)/helpers/hv_layout.py $(ROOT)/helpers/row_layout.py
	$(RUN) env HELPERS=$(ROOT)/helpers NETLIST=$< OUT=build/layout klayout -b -r layout/$*.py > build/layout/generate_$*.log 2>&1

build/layout/comparator.gds: build/layout/comparator.cdl layout/comparator.py layout/dldo_unit.py $(ROOT)/helpers/hv_layout.py $(ROOT)/helpers/row_layout.py
	$(RUN) env HELPERS=$(ROOT)/helpers NETLIST=$< OUT=build/layout klayout -b -r layout/comparator.py > build/layout/generate_comparator.log 2>&1

layout: $(foreach b,$(LAYOUTS),build/layout/$(b).gds build/layout/$(b).cdl)
	mkdir -p results
	e=0; for b in $(LAYOUTS); do d=build/layout/checks/$$b; mkdir -p $$d; cp build/layout/$$b.gds build/layout/$$b.cdl $$d; \
	  if (cd $$d && $(RUN) bash -c "python3 \$$PDK_ROOT/\$$PDK/libs.tech/klayout/tech/drc/run_drc.py --path=$$b.gds --topcell=$$b --run_dir=drc_run --no_density" > drc.log 2>&1); then x=0; else x=$$?; fi; echo "run_drc exit $$x" >> $$d/drc.log; \
	  if (cd $$d && $(RUN) bash -c "python3 \$$PDK_ROOT/\$$PDK/libs.tech/klayout/tech/lvs/run_lvs.py --layout=$$b.gds --netlist=$$b.cdl --topcell=$$b --run_dir=lvs_run --combine_devices --disable_tap_extraction" > lvs.log 2>&1); then x=0; else x=$$?; fi; echo "run_lvs exit $$x" >> $$d/lvs.log; \
	  case $$b in dldo_unit) n="$(NAMES_dldo_unit)";; comparator) n="$(NAMES_comparator)";; dldo_array) n="$(NAMES_dldo_array)";; esac; \
	  if $(RUN) klayout -b -rd path=$$d/lvs_run/$$b.lvsdb -rd names=$$n -r $(ROOT)/helpers/lvs_names.py >> $$d/lvs.log 2>&1; then x=0; else x=$$?; fi; echo "lvs_names exit $$x" >> $$d/lvs.log; \
	  cp $$d/drc.log results/cells_drc_$$b.log; cp $$d/lvs.log results/cells_lvs_$$b.log; cp $$d/lvs_run/$${b}_extracted.cir results/cells_extracted_$$b.cir; cp build/layout/generate_$$b.log results/cells_generate_$$b.log; \
	  if grep -q "DRC Check Passed" results/cells_drc_$$b.log && grep -qx "run_drc exit 0" results/cells_drc_$$b.log; then c=0; else c=1; fi; $(SAVE) cells_drc_$$b $$c results/cells_drc_$$b.log results/cells_generate_$$b.log || e=1; \
	  if grep -q "PASS (netlists match)" results/cells_lvs_$$b.log && grep -qx "run_lvs exit 0" results/cells_lvs_$$b.log && grep -qx "lvs_names exit 0" results/cells_lvs_$$b.log; then c=0; else c=1; fi; $(SAVE) cells_lvs_$$b $$c results/cells_lvs_$$b.log results/cells_extracted_$$b.cir || e=1; done; exit $$e

build/layout/%_pex.spice: build/layout/%.gds layout/extract.tcl
	cd build/layout && $(RUN) env CELL=$* bash -c 'magic -dnull -noconsole -rcfile $$PDK_ROOT/$$PDK/libs.tech/magic/ihp-sg13g2.magicrc ../../layout/extract.tcl' > extract_$*.log 2>&1
	grep -q '^.ends' $@

build/post/unit_sch_%/unit.txt: tests/unit_post.cir build/layout/unit_sizes.inc design/shifter_hv.cir design/dldo_unit.cir
	mkdir -p $(@D)
	cp $< $(@D); cat build/layout/unit_sizes.inc design/shifter_hv.cir design/dldo_unit.cir > $(@D)/dut.cir; $(call hv_corner,$*) > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b unit_post.cir > unit.log 2>&1
	$(CHECK) $(@D)/unit.log

build/post/unit_ext_%/unit.txt: tests/unit_post.cir build/layout/dldo_unit_pex.spice build/layout/dldo_unit.cdl
	mkdir -p $(@D)
	cp $< $(@D); $(call wrap,dldo_unit) > $(@D)/dut.cir; $(call hv_corner,$*) > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b unit_post.cir > unit.log 2>&1
	$(CHECK) $(@D)/unit.log

build/post/array_sch_%/array.txt: tests/array_post.cir build/layout/unit_sizes.inc design/shifter_hv.cir design/dldo_unit.cir build/layout/dldo_array.cir
	mkdir -p $(@D)
	cp $< $(@D); cat build/layout/unit_sizes.inc design/shifter_hv.cir design/dldo_unit.cir build/layout/dldo_array.cir > $(@D)/dut.cir; $(call hv_corner,$*) > $(@D)/corner.inc; $(ONS) > $(@D)/ons.inc
	cd $(@D) && $(RUN) ngspice -b array_post.cir > array.log 2>&1
	$(CHECK) $(@D)/array.log

build/post/array_ext_%/array.txt: tests/array_post.cir build/layout/dldo_array_pex.spice build/layout/dldo_array.cdl
	mkdir -p $(@D)
	cp $< $(@D); $(call wrap,dldo_array) > $(@D)/dut.cir; $(call hv_corner,$*) > $(@D)/corner.inc; $(ONS) > $(@D)/ons.inc
	cd $(@D) && $(RUN) ngspice -b array_post.cir > array.log 2>&1
	$(CHECK) $(@D)/array.log

build/post/cmp_sch_%/cmp.txt: tests/cmp_post.cir design/comparator_sizes.inc $(ROOT)/projects/adc/design/comparator.cir
	mkdir -p $(@D)
	cp $< design/comparator_sizes.inc $(@D); cp $(ROOT)/projects/adc/design/comparator.cir $(@D)/dut.cir; $(call lv_corner,$*) > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b cmp_post.cir > cmp.log 2>&1
	$(CHECK) $(@D)/cmp.log

build/post/cmp_ext_%/cmp.txt: tests/cmp_post.cir design/comparator_sizes.inc build/layout/comparator_pex.spice build/layout/comparator.cdl
	mkdir -p $(@D)
	cp $< design/comparator_sizes.inc $(@D); $(call wrap,comparator) > $(@D)/dut.cir; $(call lv_corner,$*) > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b cmp_post.cir > cmp.log 2>&1
	$(CHECK) $(@D)/cmp.log

post_layout: $(POST)
	mkdir -p results
	for f in $(POST); do cp $$f results/cells_$$(basename $$(dirname $$f)).txt; done
	e=0; for k in unit array cmp; do \
	  if $(PY) $(ROOT)/helpers/cells_results.py $$k results/cells_$${k}_ext_*.txt > results/cells_post_$$k.log 2>&1; then c=0; else c=1; fi; \
	  $(SAVE) cells_post_$$k $$c results/cells_post_$$k.log results/cells_$${k}_*.txt || e=1; done; exit $$e

cells_broken:
	mkdir -p results
	e=0; for n in $(CELLS_BROKEN); do p=broken/$$n.patch; d=build/cells_broken/$$n; mkdir -p $$d; cp -r design tests cvc layout cells.mk $$d; \
	  patch -s -F0 -d $$d -p1 < $$p; want=$$(sed -n '1s/^Expected failure: //p' $$p); run=$$(sed -n '2s/^Run: //p' $$p); log=$$(sed -n '3s/^Log: //p' $$p); \
	  if $(MAKE) -C $$d -f cells.mk $$run > $$d/make.log 2>&1; then c=1; elif [ -n "$$want" ] && grep -qF -- "$$want" $$d/$$log; then c=0; else c=2; fi; \
	  cp $$d/$$log results/$$n.log; $(SAVE) $$n $$c results/$$n.log || e=1; done; exit $$e

.PHONY: cvc layout post_layout cells_broken
.SECONDARY:
.DELETE_ON_ERROR:
