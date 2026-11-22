# Runs JKU 5T OTA netlist structural checks locally (make test) and container ngspice CACE typical/corner runs (make typ | corners).
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
ROOT := $(shell git rev-parse --show-toplevel)
RUN := $(ROOT)/setup/run.sh
PYTHON ?= python3
CORNERS := $(foreach c,tt ss ff sf fs,$(foreach t,m40 27 130,$(foreach v,1v45 1v50 1v55,build/corners/$(c)_$(t)_$(v)/cace_bench.txt)))
VOLT_1v45 := 1.45
VOLT_1v50 := 1.5
VOLT_1v55 := 1.55

.PHONY: all test typ corners clean

all: test

test:
	$(PYTHON) -m pytest -q test_netlist.py

typ: build/typ/cace_bench.txt

build/typ/cace_bench.txt: design/ota_5t.cir tests/cace_bench.cir
	mkdir -p $(@D)
	cp $^ $(@D)
	printf '.lib cornerMOSlv.lib mos_tt\n.temp 27\n.param vsupply=1.5 vin_dc=0.8 ibias=20u cload=50f mm=0\n' > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b cace_bench.cir > cace_bench.log 2>&1

corners: $(CORNERS)

build/corners/%/cace_bench.txt: design/ota_5t.cir tests/cace_bench.cir
	mkdir -p $(@D)
	cp $^ $(@D)
	printf '.lib cornerMOSlv.lib mos_%s\n.temp %s\n.param vsupply=%s vin_dc=0.8 ibias=20u cload=50f mm=0\n' \
	  $(word 1,$(subst _, ,$*)) $(subst m,-,$(word 2,$(subst _, ,$*))) $(VOLT_$(word 3,$(subst _, ,$*))) > $(@D)/corner.inc
	cd $(@D) && $(RUN) ngspice -b cace_bench.cir > cace_bench.log 2>&1

clean:
	rm -rf build
