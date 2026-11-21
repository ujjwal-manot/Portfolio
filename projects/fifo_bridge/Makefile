# fifo_bridge commands: make test | formal | cdc | timing | layout | equiv | power | mtbf | broken | all
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
ROOT := $(shell git rev-parse --show-toplevel)
RUN := $(ROOT)/setup/run.sh
SIM ?= verilator
PYTEST := $(RUN) env PYTHONPATH=$(ROOT)/helpers SIM=$(SIM) python3 -m pytest -q -s -p no:cacheprovider
SAVE := $(RUN) python3 $(ROOT)/helpers/save_result.py results/summary.json
LIB := /foss/pdks/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell
LAYOUT := layout/runs/signoff/final
ROUTED := NETLIST=../$(LAYOUT)/nl/fifo_bridge.nl.v SPEF=../$(LAYOUT)/spef/nom/fifo_bridge.nom.spef

all: test formal cdc timing layout equiv power mtbf broken

test:
	mkdir -p results
	for t in async_fifo skid_buffer fifo_bridge; do \
	  if $(PYTEST) tests/test_$$t.py > results/test_$$t.log 2>&1; then c=0; else c=$$?; fi; \
	  $(SAVE) test_$$t $$c results/test_$$t.log; done

formal:
	mkdir -p build results
	for t in fifo_proof skid_proof bridge_check fifo_reach skid_reach bridge_reach; do \
	  if (cd formal && $(RUN) sby -f --prefix ../build/formal fifo_rules.sby $$t) > results/formal_$$t.log 2>&1; then c=0; else c=$$?; fi; \
	  $(SAVE) formal_$$t $$c results/formal_$$t.log; done

timing:
	mkdir -p build results
	$(RUN) bash -c 'cp $(LIB)_slow_1p08V_125C.lib build/slow.lib; cp $(LIB)_typ_1p20V_25C.lib build/typ.lib; cp $(LIB)_fast_1p32V_m40C.lib build/fast.lib'
	if (cd timing && $(RUN) yosys -s synth.ys) > results/synth.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) synth $$c results/synth.log
	for k in slow typ fast; do \
	  if (cd timing && $(RUN) env CORNER=$$k sta -no_init -exit timing.tcl) > results/timing_$$k.log 2>&1; then c=0; else c=$$?; fi; \
	  python3 timing/sim_sdf.py build/fifo_bridge_$$k.sdf build/fifo_bridge_$${k}_sim.sdf; \
	  $(SAVE) timing_$$k $$c results/timing_$$k.log; done

layout: timing
	echo "flow did not finish" > results/layout.log
	if (cd layout && $(RUN) librelane config.json --run-tag signoff --overwrite) > results/layout_flow.log 2>&1 && $(RUN) python3 layout/metrics.py $(LAYOUT)/metrics.json > results/layout.log 2>&1; then c=0; else c=$$?; fi; \
	  $(SAVE) layout $$c results/layout_flow.log results/layout.log
	for k in slow typ fast; do \
	  if (cd timing && $(RUN) env CORNER=$$k $(ROUTED) sta -no_init -exit timing.tcl) > results/timing_routed_$$k.log 2>&1; then c=0; else c=$$?; fi; \
	  python3 timing/sim_sdf.py $$(ls $(LAYOUT)/sdf/nom_$${k}_*/*.sdf) build/routed_$${k}_sim.sdf; \
	  $(SAVE) timing_routed_$$k $$c results/timing_routed_$$k.log; done

power: timing layout
	if $(PYTEST) tests/test_sim_sdf.py > results/test_sim_sdf.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) test_sim_sdf $$c results/test_sim_sdf.log
	if $(PYTEST) tests/test_gates.py > results/test_gates.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) test_gates $$c results/test_gates.log
	for k in slow typ fast; do for n in mapped routed; do \
	  d=$$(ls -d build/icarus_fifo_bridge_test_gates_*$${k^^}* | if [ $$n = routed ]; then grep ROUTED; else grep -v ROUTED; fi); \
	  $(RUN) fst2vcd -f $$d/fifo_bridge.fst -o build/gates_$${n}_$$k.vcd > /dev/null; \
	  if [ $$n = routed ]; then w="$(ROUTED)"; else w=; fi; \
	  if (cd timing && $(RUN) env CORNER=$$k VCD=../build/gates_$${n}_$$k.vcd $$w sta -no_init -exit power.tcl) > results/power_$${n}_$$k.log 2>&1; then c=0; else c=$$?; fi; \
	  $(SAVE) power_$${n}_$$k $$c results/power_$${n}_$$k.log; done; done

cdc: timing
	$(RUN) yosys -q -p 'read_verilog -sv $(addprefix design/,sync2.sv reset_sync.sv async_fifo.sv skid_buffer.sv fifo_bridge.sv); prep -flatten -top fifo_bridge; memory_map; opt_clean; write_json build/cdc.json'
	$(RUN) yosys -q -p 'read_liberty -lib build/slow.lib; read_verilog build/fifo_bridge_cells.v; hierarchy -top fifo_bridge; write_json build/cdc_cells.json'
	for n in cdc cdc_cells; do \
	  if $(RUN) python3 $(ROOT)/helpers/cdc_check.py build/$$n.json fifo_bridge cdc/waivers.txt s_tvalid=s_clk s_tdata=s_clk s_tlast=s_clk m_tready=m_clk > results/$$n.log 2>&1; then c=0; else c=$$?; fi; \
	  $(SAVE) $$n $$c results/$$n.log; done

CORNER_tt := 1.2 27
CORNER_ss := 1.08 125
CORNER_ff := 1.32 -40
V0_rise := 0 v1={vsupply}
V0_fall := {vsupply} v1=0
EDGES := $(foreach m,tt ss ff,$(foreach e,rise fall,build/mtbf/$(m)_$(e)/edge.txt))

mtbf: $(EDGES)
	for f in $(EDGES); do cp $$f results/mtbf_$$(basename $$(dirname $$f)).txt; done
	if $(RUN) python3 mtbf/mtbf.py results/mtbf_*_*.txt > results/mtbf.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) mtbf $$c results/mtbf.log results/extract.log results/mtbf_*_*.txt

equiv: timing
	if (cd formal && $(RUN) eqy -f -d ../build/equiv equiv.eqy) > results/equiv.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) equiv $$c results/equiv.log

build/mtbf/dfrbpq_pex.spice: mtbf/extract.tcl
	mkdir -p build/mtbf results
	(cd mtbf && $(RUN) bash -c 'magic -dnull -noconsole -rcfile $$PDK_ROOT/$$PDK/libs.tech/magic/ihp-sg13g2.magicrc extract.tcl') > results/extract.log 2>&1

build/mtbf/%/edge.txt: mtbf/edge.cir build/mtbf/dfrbpq_pex.spice
	mkdir -p $(@D)
	cp $^ $(@D)
	printf '.lib cornerMOSlv.lib mos_%s\n.param vsupply=%s\n.temp %s\n.param v0=%s\n' $(word 1,$(subst _, ,$*)) $(CORNER_$(word 1,$(subst _, ,$*))) "$(V0_$(word 2,$(subst _, ,$*)))" > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b edge.cir > edge.log 2>&1

broken:
	mkdir -p results
	for p in broken/*.patch; do n=$$(basename $$p .patch); d=build/$$n; mkdir -p $$d; cp -r design tests formal $$d; \
	  patch -s -F0 -d $$d -p1 < $$p; want=$$(sed -n '1s/^Expected failure: //p' $$p); caught=0; \
	  (cd $$d && $(PYTEST) tests/test_async_fifo.py tests/test_skid_buffer.py tests/test_fifo_bridge.py) > results/$$n.log 2>&1 || caught=1; \
	  for t in fifo_proof fifo_reach; do (cd $$d/formal && $(RUN) sby -f fifo_rules.sby $$t) >> results/$$n.log 2>&1 || caught=1; done; \
	  if [ $$caught = 0 ]; then c=1; elif [ -n "$$want" ] && grep -qF -- "$$want" results/$$n.log; then c=0; else c=2; fi; \
	  $(SAVE) broken_$$n $$c results/$$n.log; done

.PHONY: all test formal cdc timing layout equiv power mtbf broken
.DELETE_ON_ERROR:
