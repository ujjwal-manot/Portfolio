# Runs the LibreLane spm reference block verification suite.
PYTHON ?= python3

.PHONY: all test

all: test

test:
	$(PYTHON) -m pytest -q test_reference_block.py
