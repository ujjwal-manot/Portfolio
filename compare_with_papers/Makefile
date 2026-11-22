# Generates compare_with_papers/report.md from published.json and measured project logs, and runs unit tests for the report generator.
PYTHON ?= python3

.PHONY: all report test clean

all: report

report: report.md

report.md: published.json make_report.py
	$(PYTHON) make_report.py published.json .. report.md

test:
	pytest -q test_make_report.py

clean:
	rm -f report.md
