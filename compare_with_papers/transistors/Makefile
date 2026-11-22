# Runs IHP SG13G2 transistor process-spec netlist checks locally (make test) and container ngspice sweeps at TT 27 C or all corners (make typ | corners).
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
ROOT := $(shell git rev-parse --show-toplevel)
RUN := $(ROOT)/setup/run.sh
PYTHON ?= python3
CORNERS := $(foreach c,tt ss ff sf fs,build/corners/$(c)/ihp_spec.txt)

.PHONY: all test typ corners clean

all: test

test:
	$(PYTHON) -m pytest -q test_netlist.py

typ: build/typ/ihp_spec.txt

build/typ/ihp_spec.txt: tests/ihp_spec.cir
	mkdir -p $(@D)
	cp $< $(@D)
	printf '.lib cornerMOSlv.lib mos_tt\n.temp 27\n' > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b ihp_spec.cir > ihp_spec.log 2>&1

corners: $(CORNERS)

build/corners/%/ihp_spec.txt: tests/ihp_spec.cir
	mkdir -p $(@D)
	cp $< $(@D)
	printf '.lib cornerMOSlv.lib mos_%s\n.temp 27\n' $* > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b ihp_spec.cir > ihp_spec.log 2>&1

clean:
	rm -rf build
