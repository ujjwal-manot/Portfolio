# Runs the phase-domain loop and MASH-111 model unit tests for projects/frac_n_pll.
PYTHON ?= python3

.PHONY: all test

all: test

test:
	$(PYTHON) -m pytest -q tests/test_pll_loop.py
