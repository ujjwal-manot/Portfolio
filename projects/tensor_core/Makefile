# tensor_core commands: make softfloat | fma | all
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
ROOT := $(shell git rev-parse --show-toplevel)
RUN := $(ROOT)/setup/run.sh
PYTEST := $(RUN) env PYTHONPATH=$(ROOT)/helpers SIM=verilator python3 -m pytest -q -s -p no:cacheprovider
SAVE := $(RUN) python3 $(ROOT)/helpers/save_result.py results/summary.json
SOFTFLOAT := $(ROOT)/third_party/softfloat

all: fma

build/softfloat/softfloat.so:
	mkdir -p build/softfloat
	cp $(SOFTFLOAT)/build/Linux-x86_64-GCC/Makefile $(SOFTFLOAT)/build/Linux-x86_64-GCC/platform.h build/softfloat
	cd build/softfloat && $(RUN) make -s SPECIALIZE_TYPE=RISCV SOURCE_DIR=$(SOFTFLOAT)/source 'COMPILE_C=cc -c -fPIC -Werror-implicit-function-declaration -DSOFTFLOAT_FAST_INT64 $$(SOFTFLOAT_OPTS) $$(C_INCLUDES) -O2 -o $$@' > build.log 2>&1
	cd build/softfloat && $(RUN) bash -c 'gcc -shared -o softfloat.so *.o'

softfloat: build/softfloat/softfloat.so

fma: build/softfloat/softfloat.so
	mkdir -p results
	if $(PYTEST) tests/test_fma.py > results/test_fma.log 2>&1; then c=0; else c=$$?; fi; $(SAVE) test_fma $$c results/test_fma.log

.PHONY: all softfloat fma
