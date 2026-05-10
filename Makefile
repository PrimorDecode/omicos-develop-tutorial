# Top-level Make targets for the OmicOS developer documentation.
# Source lives in docs/source; build output lands in docs/build.

SPHINX_OPTS    ?=
SPHINX_BUILD   ?= sphinx-build
SOURCE_DIR     = docs/source
BUILD_DIR      = docs/build

.PHONY: help install html clean livehtml linkcheck

help:
	@echo "make install   — pip install -r requirements.txt"
	@echo "make html      — build HTML into docs/build/html"
	@echo "make livehtml  — auto-rebuild on file change (needs sphinx-autobuild)"
	@echo "make linkcheck — verify external links"
	@echo "make clean     — wipe docs/build"

install:
	pip install -r requirements.txt

html:
	@$(SPHINX_BUILD) -M html "$(SOURCE_DIR)" "$(BUILD_DIR)" $(SPHINX_OPTS)

livehtml:
	@sphinx-autobuild "$(SOURCE_DIR)" "$(BUILD_DIR)/html" $(SPHINX_OPTS)

linkcheck:
	@$(SPHINX_BUILD) -M linkcheck "$(SOURCE_DIR)" "$(BUILD_DIR)" $(SPHINX_OPTS)

clean:
	rm -rf "$(BUILD_DIR)"
