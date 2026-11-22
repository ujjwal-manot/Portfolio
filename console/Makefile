# Starts, builds, or tests the read-only EdgeSense-130 console using the pinned Node 24 toolchain when present.
NODE_BIN := $(abspath ../third_party/node/bin)
ifneq ($(wildcard $(NODE_BIN)/npm),)
export PATH := $(NODE_BIN):$(PATH)
endif

.PHONY: all dev install build test

all: dev

install:
	npm ci

dev:
	npm run dev

build:
	npm run build

test:
	npm test
