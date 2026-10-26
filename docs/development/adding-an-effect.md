# Adding an effect

New to DSP or Faust? Read [How it works](how-it-works.md) first. One effect is one `src/<name>.dsp`. The Makefile discovers effects automatically, so there is no list to update. The steps below take an effect from an idea to a published page. BassDrive, a modelled effect, is the worked example for the mechanics. For where ideas come from and how to write them up, see [Designing new sounds](designing-new-sounds.md) first.

## 1. Write the notes

Write the reasoning down before any DSP. `REUSE.toml` already licenses everything under `docs/` as CC BY 4.0.

**Original or circuit-inspired effects** get `docs/<name>/design-notes.md`: the sonic idea, prior art and inspirations, the block diagram, every constant with its confidence level and intent, the measurable targets the tests will check, and the open questions. [Designing new sounds](designing-new-sounds.md#writing-design-notes) has the outline.

**Modelled effects**, and the borrowed part of a circuit-inspired one, get `docs/<name>/circuit-notes.md`. Use [the BassDrive notes](../bassdrive/circuit-notes.md) as the template. The notes must cover:

- the documented controls and specifications
- the block diagram
- each stage with its component values and the corner frequencies derived from them
- the confidence level of every claim (documented, reported, inferred or chosen)
- a numbered source list with links
- the open questions

If any hardware is referenced, add its manufacturer and product names to `tools/trademarks.txt` if they aren't listed yet. The `no-trademarks` pre-commit hook then fails if one of them reaches a file name, a `declare` line or a UI label (see [Linting and CI](ci.md#extending-the-trademark-deny-list)).

## 2. Write the DSP

Create `src/<name>.dsp`. Start with an SPDX header and a comment showing the signal flow, then declare the metadata:

```faust
declare name        "BassDrive";
declare description "Bass overdrive with clean blend and two-band EQ";
declare author      "Joe Heffer";
declare license     "MIT";              // SPDX identifier
declare version     "0.1.0";            // major.minor.micro; every new effect starts at 0.1.0
declare lv2class    "DistortionPlugin"; // LV2 class without its prefix
declare homepage    "https://github.com/Joe-Heffer/faust-pedalkit";

import("stdfaust.lib");
pk = library("pedalkit.lib");
```

The LV2 plugin takes its name from `declare name`. `tools/fix-ttl.py` turns `license`, `version`, `lv2class` and `homepage` into the LV2 metadata that `lv2lint` requires.

### Controls

Every control has a unit, a sensible range and default, a tooltip and smoothing. The `[n]` prefix fixes the order, and the test scripts address sliders by their label.

```faust
gain = hslider("[2]Gain [unit:%] [tooltip:Amount of drive]", 50, 0, 100, 0.1) / 100 : si.smoo;
```

### Constants

Put the constants, circuit values and design choices alike, at the top as named values, each with a comment saying where it came from or what it is for:

```faust
R31     = 3.3e3;   // pre-emphasis shunt resistor (reported)
stage2G = 3.0;     // stage 2 fixed gain (chosen, tuned by measurement)
```

### Nonlinearities and oversampling

- Put every nonlinearity inside `pk.oversample4(f)`. `f` **must be memoryless**, a pure waveshaper, because it is applied to four parallel phase streams. Filters belong outside it.
- Delay any dry or parallel path that meets an oversampled path by `@(pk.os4Latency)`, or the blend will comb-filter.
- Report the latency, so hosts can compensate it:

    ```faust
    latency = pk.os4Latency
            : hbargraph("Latency [unit:samples] [lv2:reportsLatency] [lv2:integer]", 0, 256);
    ```

### Output and DC

- Use `fi.dcblockerat(5)` (5 Hz), not `fi.dcblocker` (about 35 Hz), on anything meant for bass. A 35 Hz blocker already takes the edge off a low E (41 Hz) or a low B (31 Hz).
- End `process` with `pk.safety(0.989)`, so no sample can exceed 0 dBFS.

## 3. Write the tests

Add `tests/<name>/test_*.py`. Each script imports from `fxtest` and ends with `finish()`. The minimum set is:

- silence in gives silence out
- peak ≤ 0 dBFS at the extreme settings
- frequency response at several settings
- harmonic content
- an aliasing comparison (`RENDER` against `RENDER_1X`) whenever the effect oversamples
- for an original or circuit-inspired effect, the measurable targets from the design notes

Save every plot as SVG and the numbers behind it as CSV. See [Tests and measurements](testing.md) for the helpers.

## 4. Build and check

```sh
make lv2 lint test FX=<name>
make vst3 pluginval FX=<name>
make clap clap-validate FX=<name>
make check                       # pre-commit run --all-files
```

Fix every `lv2lint`, VST3 validator, pluginval, clap-validator and pre-commit failure, and read the plots before reporting results.

## 5. Document it

- Add a row to the effect table in `README.md`, on the [home page](../index.md) and on the [effects page](../effects/index.md).
- Add `docs/<name>/index.md`, modelled on [the BassDrive page](../bassdrive/index.md): controls, signal path, measured behaviour with the plots embedded from `../measurements/<name>/`, what to tune by ear, and known limitations. For an original effect, open with the idea rather than a reference device.
- Add `docs/<name>/changelog.md`, modelled on [the BassDrive changelog](../bassdrive/changelog.md), with a `## [0.1.0]` section. Every effect starts at version 0.1.0 and is released on its own (see [Releasing](releasing.md)).
- Add the effect page, its notes and its changelog to `nav` in `mkdocs.yml`, under *Effects*.
- Build the site with `make test docs` (install the tools with `pip install -r tools/docs-requirements.txt`) and check that it has no warnings. The build is strict, so every warning fails it.

## Presets (optional)

Add `src/<name>.presets.toml`, using `src/basspreamp.presets.toml` as the template: a list of `[[preset]]` tables, each with a `name`, a `comment` and a `controls` table keyed by UI label. Set every control, because LV2 hosts leave unlisted controls where they were. The settings are chosen values, and the file says so. Add `tests/<name>/test_presets.py` to render each preset, check its peak and loudness-match it with `loudness()`, and list the presets in the README and on the effect's docs page.

## 6. Report back

Finish with a short summary covering:

- what works, backed by test results
- what is approximate, referring to the "chosen" values
- what a human should check by listening, naming the constant or control to adjust
