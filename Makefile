# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
# Faust effects: every src/<name>.dsp is one effect.
#
#   make lv2          build LV2 bundles into build/<name>.lv2
#   make vst3         build VST3 bundles into build/<name>.vst3
#   make clap         build CLAP plugins into build/<name>.clap
#   make standalone   build JACK applications (Qt GUI) into build/<name>/
#   make lint         run lv2lint on each LV2 bundle
#   make pluginval    run pluginval on each VST3 bundle
#   make clap-validate  run clap-validator on each CLAP plugin
#   make test         build the offline renderers and run tests/<name>/
#   make describe     write each effect's JSON description and SVG block diagram
#   make dist         pack each effect's LV2, VST3 and CLAP plugins into a release tarball in build/dist/
#   make web          build the browser demo (WebAssembly and page) into build/web/
#   make web-test     compare the browser build with the native renderer and time it
#   make docs         build the documentation site into build/site (run `make test` and `make web` first)
#   make docs-serve   preview the documentation site at http://127.0.0.1:8000/
#   make check        run every pre-commit hook on every file (as CI does)
#   make format       fix Python lint and formatting with ruff
#   make install      copy the LV2 bundles into ~/.lv2
#   make install-vst3 copy the VST3 bundles into ~/.vst3
#   make install-clap copy the CLAP plugins into ~/.clap
#   make uninstall    remove them from ~/.lv2, ~/.vst3 and ~/.clap
#   make clean        remove build/ and tests/out/, keeping the downloaded VST3 SDK
#   make distclean    remove build/, tests/out/ and tools/web/node_modules/ entirely
#   make help         list these targets and the effects
#   make image        build the toolchain image from the Dockerfile (or DOCKERFILE)
#   make container    run the RUN targets in that image (default RUN="lv2 lint test")
#
# By default every effect is built. Restrict with FX, e.g. `make test FX=bassdrive`.

EFFECTS    := $(basename $(notdir $(wildcard src/*.dsp)))
FX         ?= $(EFFECTS)
# An empty FX (e.g. from an unset workflow input) also means every effect.
ifeq ($(strip $(FX)),)
override FX := $(EFFECTS)
endif
UNKNOWN_FX := $(filter-out $(EFFECTS),$(FX))
ifneq ($(UNKNOWN_FX),)
$(error Unknown effect(s): $(UNKNOWN_FX). Choose from: $(EFFECTS))
endif
LIBS       := $(wildcard src/lib/*.lib)
BUILD      := build
URI_PREFIX := urn:pedalkit
LV2DIR     ?= $(HOME)/.lv2
VST3DIR    ?= $(HOME)/.vst3
CLAPDIR    ?= $(HOME)/.clap

# VST3 SDK (MIT since 3.8), fetched into build/ on first use. Point VST3_SDK
# at an existing checkout to skip the download.
VST3_SDK_TAG := v3.8.1_build_84
VST3_SDK     ?= $(BUILD)/vst3sdk
VST3_ARCH    := tools/vst3/faust-vst3.cpp
PLUGINVAL    ?= pluginval

# CLAP headers (MIT), fetched into build/ on first use. Point CLAP_SDK at an
# existing checkout of github.com/free-audio/clap to skip the download.
CLAP_TAG       := 1.2.10
CLAP_SDK       ?= $(BUILD)/clap
CLAP_ARCH      := tools/clap/faust-clap.cpp
CLAP_VALIDATOR ?= clap-validator

CXX        ?= g++
CXXFLAGS   ?= -O2 -std=c++17
# Extra flags for linking the plugins. Dockerfile.release sets
# -static-libgcc for release builds.
LDFLAGS    ?=
FAUST_INC  := $(shell faust --includedir 2>/dev/null)
ARCH       := tests/lib/render-arch.cpp
MKDOCS     ?= mkdocs
NODE       ?= node
NPM        ?= npm
PRE_COMMIT ?= pre-commit

# Release tarballs (make dist): one per effect, named from the effect's own
# `declare version`, e.g. build/dist/bassdrive-0.1.0-linux-x86_64.tar.gz.
fxversion   = $(shell sed -n 's/^ *declare *version *"\([^"]*\)".*/\1/p' src/$(1).dsp)
DIST       := $(BUILD)/dist
distname    = $(1)-$(call fxversion,$(1))-linux-$(shell uname -m)

# Browser demo (make web): faustwasm, pinned in tools/web/package-lock.json,
# compiles each effect to WebAssembly and provides the AudioWorklet runtime
# that the page in web/ loads. The result is a static site in build/web/.
WEB        := $(BUILD)/web
WEB_NODE   := tools/web/node_modules/.package-lock.json
FAUSTWASM  := tools/web/node_modules/@grame/faustwasm

# Toolchain image (see Dockerfile). CONTAINER may be docker or podman; extra
# `run` options go in CONTAINER_FLAGS.
CONTAINER       ?= docker
DOCKERFILE      ?= Dockerfile
IMAGE           ?= pedalkit-build
RUN             ?= lv2 lint test
CONTAINER_FLAGS ?=
# Run as the caller so build/ and tests/out/ stay theirs. Rootless Podman
# maps the caller's UID with keep-id instead.
ifneq ($(findstring podman,$(CONTAINER)),)
CONTAINER_USER  := --userns=keep-id
else
CONTAINER_USER  := --user $(shell id -u):$(shell id -g)
endif

.PHONY: all lv2 vst3 clap standalone lint pluginval clap-validate test describe dist web web-test docs docs-serve check format \
        install install-vst3 install-clap uninstall clean distclean help \
        image container
.SECONDARY:
# A failed recipe deletes its half-written target, so the next run rebuilds it.
.DELETE_ON_ERROR:

all: lv2

lv2: $(foreach f,$(FX),$(BUILD)/$(f).lv2/manifest.ttl)

vst3: $(foreach f,$(FX),$(BUILD)/$(f)/vst3.stamp)

clap: $(foreach f,$(FX),$(BUILD)/$(f).clap)

standalone: $(foreach f,$(FX),$(BUILD)/$(f)/standalone.stamp)

lint: lv2
	@status=0; for f in $(FX); do \
	    echo "== lv2lint $$f"; \
	    lv2lint -I $(BUILD)/$$f.lv2/ $(URI_PREFIX)/$$f || status=1; \
	done; exit $$status

# Strictness 10 is pluginval's most thorough level. There is no GUI to test.
pluginval: vst3
	@status=0; for f in $(FX); do \
	    echo "== pluginval $$f"; \
	    $(PLUGINVAL) --strictness-level 10 --skip-gui-tests --validate-in-process \
	        --validate $(BUILD)/$$f.vst3 || status=1; \
	done; exit $$status

clap-validate: clap
	@status=0; for f in $(FX); do \
	    echo "== clap-validator $$f"; \
	    $(CLAP_VALIDATOR) validate --only-failed $(BUILD)/$$f.clap || status=1; \
	done; exit $$status

test: $(foreach f,$(FX),$(BUILD)/$(f)/render $(BUILD)/$(f)/render_1x)
	@status=0; for f in $(FX); do bash tests/run.sh $$f || status=1; done; exit $$status

describe: $(foreach f,$(FX),$(BUILD)/$(f)/describe.stamp)

# The page in web/ lists the effects from effects.json and builds each one's
# controls from its dsp-meta.json (the same description as `make describe`).
web: $(foreach f,$(FX),$(WEB)/$(f)/dsp-module.wasm)
	mkdir -p $(WEB)/faustwasm
	cp web/index.html web/demo.js web/demo.css $(WEB)/
	cp $(FAUSTWASM)/dist/esm/index.js $(FAUSTWASM)/dist/esm/index.js.map $(FAUSTWASM)/COPYING.txt $(WEB)/faustwasm/
	printf '[%s]\n' "$$(printf '"%s",' $(FX) | sed 's/,$$//')" > $(WEB)/effects.json

# Compares the WebAssembly build with the native renderer, so it needs both.
web-test: web $(foreach f,$(FX),$(BUILD)/$(f)/render)
	FX=web WEB_FX="$(FX)" NODE=$(NODE) PYTHONPATH=tests/lib python3 tests/web/test_wasm.py

$(WEB_NODE): tools/web/package.json tools/web/package-lock.json
	$(NPM) ci --prefix tools/web --no-audit --no-fund

$(WEB)/%/dsp-module.wasm: src/%.dsp $(LIBS) $(WEB_NODE)
	mkdir -p $(@D)
	$(NODE) $(FAUSTWASM)/scripts/faust2wasm.js $< $(@D) -I src/lib -no-template

# The site embeds the plots and CSV data from tests/out/ and the browser demo
# from build/web/, so run `make test web` first (see tools/mkdocs_hooks.py). Tools: pip install -r tools/docs-requirements.txt
docs:
	$(MKDOCS) build --strict

docs-serve:
	$(MKDOCS) serve

check:
	$(PRE_COMMIT) run --all-files

# Uses the ruff pinned in .pre-commit-config.yaml, so the result matches CI.
# pre-commit exits non-zero whenever a hook changes a file, so only the last
# run decides the status: it fails if ruff left anything it could not fix.
format:
	@$(PRE_COMMIT) run ruff-check --all-files || true
	@$(PRE_COMMIT) run ruff-format --all-files || true
	$(PRE_COMMIT) run ruff-check --all-files

install: lv2
	mkdir -p $(LV2DIR)
	for f in $(FX); do rm -rf $(LV2DIR)/$$f.lv2 && cp -r $(BUILD)/$$f.lv2 $(LV2DIR)/; done

install-vst3: vst3
	mkdir -p $(VST3DIR)
	for f in $(FX); do rm -rf $(VST3DIR)/$$f.vst3 && cp -r $(BUILD)/$$f.vst3 $(VST3DIR)/; done

install-clap: clap
	mkdir -p $(CLAPDIR)
	for f in $(FX); do cp $(BUILD)/$$f.clap $(CLAPDIR)/; done

# Release tarballs: for each effect, its plugins in one folder per format,
# plus install.sh, which copies them into ~/.lv2, ~/.vst3 and ~/.clap, and the
# effect's changelog. Build them with Dockerfile.release so the plugins load
# on older distributions (see docs/development/releasing.md).
dist: lv2 vst3 clap
	rm -rf $(DIST)
	$(foreach f,$(FX),$(call dist-one,$(f),$(call distname,$(f))))
	cd $(DIST) && sha256sum *.tar.gz > SHA256SUMS

define dist-one
mkdir -p $(DIST)/$(2)/lv2 $(DIST)/$(2)/vst3 $(DIST)/$(2)/clap
	cp -r $(BUILD)/$(1).lv2 $(DIST)/$(2)/lv2/
	cp -r $(BUILD)/$(1).vst3 $(DIST)/$(2)/vst3/
	cp $(BUILD)/$(1).clap $(DIST)/$(2)/clap/
	cp tools/release/install.sh tools/release/README.txt LICENSE $(DIST)/$(2)/
	cp docs/$(1)/changelog.md $(DIST)/$(2)/CHANGELOG.md
	tar -C $(DIST) --sort=name --owner=0 --group=0 --numeric-owner -czf $(DIST)/$(2).tar.gz $(2)

endef

uninstall:
	for f in $(FX); do rm -rf $(LV2DIR)/$$f.lv2 $(VST3DIR)/$$f.vst3 $(CLAPDIR)/$$f.clap; done

# faust2lv2 and faust2jaqt build in the current directory, so each effect is
# staged in build/<name>/ with the shared libraries copied alongside.
$(BUILD)/%/stage.stamp: src/%.dsp $(LIBS)
	mkdir -p $(@D)
	cp $< $(LIBS) $(@D)/
	touch $@

# Factory presets are optional: src/<name>.presets.toml, if present, is added
# to the bundle as LV2 presets by tools/make-presets.py.
.SECONDEXPANSION:
$(BUILD)/%.lv2/manifest.ttl: $(BUILD)/%/stage.stamp tools/fix-ttl.py tools/make-presets.py $$(wildcard src/$$*.presets.toml)
	cd $(BUILD)/$* && $(if $(LDFLAGS),CXXFLAGS="$(LDFLAGS)") faust2lv2 -nomidicc -uri-prefix $(URI_PREFIX) $*.dsp
	rm -rf $(BUILD)/$*.lv2
	mv $(BUILD)/$*/$*.lv2 $(BUILD)/
	python3 tools/fix-ttl.py src/$*.dsp $(BUILD)/$*.lv2/$*.ttl
	if [ -f src/$*.presets.toml ]; then \
	    python3 tools/make-presets.py src/$*.presets.toml $(BUILD)/$*.lv2 $(URI_PREFIX)/$*; \
	fi

# VST3: faust compiles the effect into the architecture in tools/vst3/,
# tools/vst3-meta.py writes its names and class ID, and the SDK's CMake
# builds the bundle, running Steinberg's validator on it as a post-build
# step. Only the SDK submodules the build needs are fetched.
$(VST3_SDK)/CMakeLists.txt:
	rm -rf $(VST3_SDK)
	git -c advice.detachedHead=false clone --quiet --depth 1 --branch $(VST3_SDK_TAG) \
	    https://github.com/steinbergmedia/vst3sdk $(VST3_SDK)
	git -C $(VST3_SDK) submodule update --quiet --init --depth 1 \
	    base pluginterfaces public.sdk cmake

$(BUILD)/%/vst3.stamp: src/%.dsp $(LIBS) $(VST3_ARCH) tools/vst3/CMakeLists.txt \
                       tools/vst3-meta.py tools/dspmeta.py | $(VST3_SDK)/CMakeLists.txt
	mkdir -p $(@D)/vst3
	faust -I src/lib -a $(VST3_ARCH) -o $(@D)/vst3/$*.cpp $<
	python3 tools/vst3-meta.py $< $* $(@D)/vst3/plugin_meta.h
	cmake -S tools/vst3 -B $(@D)/vst3/build -DCMAKE_BUILD_TYPE=Release \
	    -DFX_NAME=$* -DFX_VERSION=$(call fxversion,$*) \
	    -DFX_GEN_DIR=$(abspath $(@D)/vst3) -DFAUST_INC=$(FAUST_INC) \
	    -DVST3_SDK_DIR=$(abspath $(VST3_SDK)) \
	    -DCMAKE_SHARED_LINKER_FLAGS="$(LDFLAGS)" -DCMAKE_MODULE_LINKER_FLAGS="$(LDFLAGS)"
	cmake --build $(@D)/vst3/build --config Release --parallel
	rm -rf $(BUILD)/$*.vst3
	cp -r $(@D)/vst3/build/VST3/Release/$*.vst3 $(BUILD)/
	touch $@

# CLAP: faust compiles the effect into the architecture in tools/clap/,
# tools/clap-meta.py writes its ID, names and features, and the result is
# linked straight into a shared object. CLAP is a header-only C API, so no
# SDK library or CMake is involved.
$(CLAP_SDK)/include/clap/clap.h:
	rm -rf $(CLAP_SDK)
	git -c advice.detachedHead=false clone --quiet --depth 1 --branch $(CLAP_TAG) \
	    https://github.com/free-audio/clap $(CLAP_SDK)

$(BUILD)/%.clap: src/%.dsp $(LIBS) $(CLAP_ARCH) tools/clap-meta.py tools/dspmeta.py \
                 | $(CLAP_SDK)/include/clap/clap.h
	mkdir -p $(BUILD)/$*/clap
	faust -I src/lib -a $(CLAP_ARCH) -o $(BUILD)/$*/clap/$*.cpp $<
	python3 tools/clap-meta.py $< $* $(BUILD)/$*/clap/plugin_meta.h
	$(CXX) $(CXXFLAGS) -shared -fPIC -fvisibility=hidden \
	    -I$(BUILD)/$*/clap -I$(FAUST_INC) -I$(CLAP_SDK)/include \
	    $(BUILD)/$*/clap/$*.cpp $(LDFLAGS) -o $@

$(BUILD)/%/standalone.stamp: $(BUILD)/%/stage.stamp
	cd $(BUILD)/$* && (command -v faust2jaqt >/dev/null && faust2jaqt $*.dsp || faust2jack $*.dsp)
	touch $@

# Format-neutral description of each effect: every control's label, unit,
# range and default (build/<name>/<name>.dsp.json), plus the block diagram
# (SVG, in build/<name>/<name>-svg/).
$(BUILD)/%/describe.stamp: $(BUILD)/%/stage.stamp
	cd $(BUILD)/$* && faust -json -svg $*.dsp -o /dev/null
	touch $@

# Offline renderer for the tests, plus a 1x variant (oversample4 swapped for
# oversample1) used only to measure what the oversampling buys.
$(BUILD)/%/render: src/%.dsp $(LIBS) $(ARCH)
	mkdir -p $(@D)
	faust -I src/lib -a $(ARCH) -o $(@D)/render.cpp $<
	$(CXX) $(CXXFLAGS) -I$(FAUST_INC) $(@D)/render.cpp -o $@

$(BUILD)/%/render_1x: src/%.dsp $(LIBS) $(ARCH)
	mkdir -p $(@D)
	sed 's/oversample4(/oversample1(/g' $< > $(@D)/$*_1x.dsp
	faust -I src/lib -a $(ARCH) -o $(@D)/render_1x.cpp $(@D)/$*_1x.dsp
	$(CXX) $(CXXFLAGS) -I$(FAUST_INC) $(@D)/render_1x.cpp -o $@

# The VST3 SDK clone is slow to fetch and rarely changes, so `clean` keeps it.
clean:
	rm -rf tests/out
	[ ! -d $(BUILD) ] || find $(BUILD) -mindepth 1 -maxdepth 1 ! -name vst3sdk -exec rm -rf {} +

distclean:
	rm -rf $(BUILD) tests/out tools/web/node_modules

help:
	@sed -n 's/^#   make /make /p' $(firstword $(MAKEFILE_LIST))
	@echo
	@echo "Effects: $(EFFECTS)"

image:
	$(CONTAINER) build -f $(DOCKERFILE) -t $(IMAGE) .

container: image
	$(CONTAINER) run --rm $(CONTAINER_USER) $(CONTAINER_FLAGS) -v "$(CURDIR)":/src -w /src \
	    $(IMAGE) make $(RUN) FX="$(FX)"
