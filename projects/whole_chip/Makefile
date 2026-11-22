# Runs the whole_chip end-to-end firmware (fir8_dvfs.hex on cpu_model.py), analog headroom, and DVFS energy scaling verification suite.
PYTHON ?= python3

.PHONY: all test

all: test

test:
	$(PYTHON) -m pytest -q tests/test_whole_chip.py
