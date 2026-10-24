# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
# Faust effects: every src/<name>.dsp is one effect.
#
#   make lv2          build LV2 bundles into build/<name>.lv2
#   make standalone   build JACK applications (Qt GUI) into build/<name>/
#   make lint         run lv2lint on each bundle
#   make test         build the offline renderers and run tests/<name>/
#   make describe     write each effect's JSON description and SVG block diagram
#   make install      copy the bundles into ~/.lv2
#   make uninstall    remove them from ~/.lv2
#   make clean        remove build/ and tests/out/
#
# By default every effect is built. Restrict with FX, e.g. `make test FX=bassdrive`.

EFFECTS    := $(basename $(notdir $(wildcard src/*.dsp)))
FX         ?= $(EFFECTS)
LIBS       := $(wildcard src/lib/*.lib)
BUILD      := build
URI_PREFIX := urn:pedalkit
LV2DIR     ?= $(HOME)/.lv2

CXX        ?= g++
CXXFLAGS   ?= -O2 -std=c++17
FAUST_INC  := $(shell faust --includedir 2>/dev/null)
ARCH       := tests/lib/render-arch.cpp

.PHONY: all lv2 standalone lint test describe install uninstall clean
.SECONDARY:

all: lv2

lv2: $(foreach f,$(FX),$(BUILD)/$(f).lv2/manifest.ttl)

standalone: $(foreach f,$(FX),$(BUILD)/$(f)/standalone.stamp)

lint: lv2
	@status=0; for f in $(FX); do \
	    echo "== lv2lint $$f"; \
	    lv2lint -I $(BUILD)/$$f.lv2/ $(URI_PREFIX)/$$f || status=1; \
	done; exit $$status

test: $(foreach f,$(FX),$(BUILD)/$(f)/render $(BUILD)/$(f)/render_1x)
	@status=0; for f in $(FX); do bash tests/run.sh $$f || status=1; done; exit $$status

describe: $(foreach f,$(FX),$(BUILD)/$(f)/describe.stamp)

install: lv2
	mkdir -p $(LV2DIR)
	for f in $(FX); do rm -rf $(LV2DIR)/$$f.lv2 && cp -r $(BUILD)/$$f.lv2 $(LV2DIR)/; done

uninstall:
	for f in $(FX); do rm -rf $(LV2DIR)/$$f.lv2; done

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
	cd $(BUILD)/$* && faust2lv2 -nomidicc -uri-prefix $(URI_PREFIX) $*.dsp
	rm -rf $(BUILD)/$*.lv2
	mv $(BUILD)/$*/$*.lv2 $(BUILD)/
	python3 tools/fix-ttl.py src/$*.dsp $(BUILD)/$*.lv2/$*.ttl
	if [ -f src/$*.presets.toml ]; then \
	    python3 tools/make-presets.py src/$*.presets.toml $(BUILD)/$*.lv2 $(URI_PREFIX)/$*; \
	fi

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
