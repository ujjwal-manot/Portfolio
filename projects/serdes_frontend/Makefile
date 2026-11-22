# Runs the 10 GBd SerDes front-end CTLE, 3-tap FFE, pad S11, and CML TX sizing unit tests for projects/serdes_frontend.
PYTHON ?= python3

.PHONY: all test

all: test

test:
	$(PYTHON) -m pytest -q tests/test_frontend_sizing.py
