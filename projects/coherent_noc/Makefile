# Runs the XY mesh, directory MESI, and CRC-16 die-to-die replay reference tests for projects/coherent_noc.
PYTHON ?= python3

.PHONY: all test

all: test

test:
	$(PYTHON) -m pytest -q tests/test_noc_model.py
