# Runs the Cummings SNUG-2002 FIFO1 Gray-code reference test and checks the broken patch applies cleanly.
PYTHON ?= python3

.PHONY: all test

all: test

test:
	$(PYTHON) -m pytest -q test_cummings_ref.py
