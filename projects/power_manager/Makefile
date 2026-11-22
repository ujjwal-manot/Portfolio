# power_manager commands: make speed | all
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
ROOT := $(shell git rev-parse --show-toplevel)
RUN := $(ROOT)/setup/run.sh
PY := $(RUN) env PYTHONPATH=$(ROOT)/helpers python3
SAVE := $(RUN) python3 $(ROOT)/helpers/save_result.py results/summary.json
SPEED_CORNERS := tt_25 ss_125 ss_m40 ff_m40 ff_125
SPEED := $(foreach c,$(SPEED_CORNERS),build/speed/$(c)/speed.txt)
TEMP_25 := 25
TEMP_125 := 125
TEMP_m40 := -40

all: speed

build/speed/%/speed.txt: tests/speed.cir
	mkdir -p $(@D)
	cp $< $(@D)
	printf '.lib cornerMOSlv.lib mos_%s\n.temp %s\n' $(word 1,$(subst _, ,$*)) $(TEMP_$(word 2,$(subst _, ,$*))) > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b speed.cir > speed.log 2>&1

speed: $(SPEED) tests/fo4.v tests/fo4.tcl
	mkdir -p build/fo4 results
	cp tests/fo4.v tests/fo4.tcl build/fo4
	for k in slow typ fast; do (cd build/fo4 && $(RUN) env CORNER=$$k sta -no_init -exit fo4.tcl) | tail -n 1 > results/fo4_$$k.txt; done
	for c in $(SPEED_CORNERS); do cp build/speed/$$c/speed.txt results/speed_$$c.txt; done
	if $(PY) $(ROOT)/helpers/speed_results.py results/speed_*.txt results/fo4_*.txt > results/speed.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) speed $$c results/speed.log results/speed_*.txt results/fo4_*.txt

.PHONY: all speed
