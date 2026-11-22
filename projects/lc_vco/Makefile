# Runs the LC VCO tank sizing, tuning band coverage, start-up, and Leeson phase-noise unit tests for projects/lc_vco.
PYTHON ?= python3

.PHONY: all test

all: test

test:
	$(PYTHON) -m pytest -q tests/test_vco_sizing.py
