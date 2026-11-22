# Runs the digital SerDes link model unit tests (PRBS, 1-tap sign-sign LMS DFE, bang-bang CDR, PAM4 slicer) for projects/serdes_link.
PYTHON ?= python3

.PHONY: all test

all: test

test:
	$(PYTHON) -m pytest -q tests/test_link_models.py
