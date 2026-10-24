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
#   make docs         build the documentation site into build/site (run `make test` first)
#   make docs-serve   preview the documentation site at http://127.0.0.1:8000/
#   make install      copy the LV2 bundles into ~/.lv2
#   make install-vst3 copy the VST3 bundles into ~/.vst3
#   make install-clap copy the CLAP plugins into ~/.clap
#   make uninstall    remove them from ~/.lv2, ~/.vst3 and ~/.clap
#   make clean        remove build/ and tests/out/
#
# By default every effect is built. Restrict with FX, e.g. `make test FX=bassdrive`.

EFFECTS    := $(basename $(notdir $(wildcard src/*.dsp)))
FX         ?= $(EFFECTS)
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
FAUST_INC  := $(shell faust --includedir 2>/dev/null)
ARCH       := tests/lib/render-arch.cpp
MKDOCS     ?= mkdocs

.PHONY: all lv2 vst3 clap standalone lint pluginval clap-validate test describe docs docs-serve \
        install install-vst3 install-clap uninstall clean
.SECONDARY:

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

# The site embeds the plots and CSV data from tests/out/, so run `make test`
# first (see tools/mkdocs_hooks.py). Tools: pip install -r tools/docs-requirements.txt
docs:
	$(MKDOCS) build --strict

docs-serve:
	$(MKDOCS) serve

install: lv2
	mkdir -p $(LV2DIR)
	for f in $(FX); do rm -rf $(LV2DIR)/$$f.lv2 && cp -r $(BUILD)/$$f.lv2 $(LV2DIR)/; done

install-vst3: vst3
	mkdir -p $(VST3DIR)
	for f in $(FX); do rm -rf $(VST3DIR)/$$f.vst3 && cp -r $(BUILD)/$$f.vst3 $(VST3DIR)/; done

install-clap: clap
	mkdir -p $(CLAPDIR)
	for f in $(FX); do cp $(BUILD)/$$f.clap $(CLAPDIR)/; done

uninstall:
	for f in $(FX); do rm -rf $(LV2DIR)/$$f.lv2 $(VST3DIR)/$$f.vst3 $(CLAPDIR)/$$f.clap; done

# faust2lv2 and faust2jaqt build in the current directory, so each effect is
# staged in build/<name>/ with the shared libraries copied alongside.
$(BUILD)/%/stage.stamp: src/%.dsp $(LIBS)
	mkdir -p $(@D)
	cp $< $(LIBS) $(@D)/
	touch $@

$(BUILD)/%.lv2/manifest.ttl: $(BUILD)/%/stage.stamp tools/fix-ttl.py
	cd $(BUILD)/$* && faust2lv2 -nomidicc -uri-prefix $(URI_PREFIX) $*.dsp
	rm -rf $(BUILD)/$*.lv2
	mv $(BUILD)/$*/$*.lv2 $(BUILD)/
	python3 tools/fix-ttl.py src/$*.dsp $(BUILD)/$*.lv2/$*.ttl

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
	    -DFX_NAME=$* -DFX_VERSION=$$(sed -n 's/^ *declare *version *"\([^"]*\)".*/\1/p' $<) \
	    -DFX_GEN_DIR=$(abspath $(@D)/vst3) -DFAUST_INC=$(FAUST_INC) \
	    -DVST3_SDK_DIR=$(abspath $(VST3_SDK))
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
	    $(BUILD)/$*/clap/$*.cpp -o $@

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

clean:
	rm -rf $(BUILD) tests/out
