# Top-level commands: make tools | check_tools | self_test | all | honesty | balance | compare | console
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
RUN := setup/run.sh
PROJECTS := $(wildcard projects/*)

tools:
	bash setup/get_tools.sh

check_tools:
	$(RUN) setup/check_tools.sh | tee setup/tools_found.txt

self_test:
	$(RUN) python3 -m pytest -q -p no:cacheprovider helpers tracking

all: self_test
	for p in $(PROJECTS); do $(MAKE) -C $$p all; done
	$(MAKE) honesty

honesty:
	$(RUN) python3 helpers/check_honesty.py

balance:
	$(RUN) python3 tracking/balance.py

compare:
	$(MAKE) -C compare_with_papers

console:
	$(MAKE) -C console

.PHONY: tools check_tools self_test all honesty balance compare console
