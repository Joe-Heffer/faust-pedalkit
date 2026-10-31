---
name: pedalkit-effect
description: Design, build, test and document a new guitar or bass effect plugin (LV2, VST3, CLAP) in this Faust Pedal Kit repository. Use when asked to add, prototype or modify an effect, write a src/<name>.dsp, add pedalkit.lib blocks, give an effect dynamics or feel (bias shift, sag, envelopes), write design or circuit notes, add effect tests or presets, turn a browser-designer sketch into an effect, or open a PR for an effect.
---

# Pedal Kit: creating an effect

This repository is a workshop for new guitar and bass effects written in Faust. One effect is one `src/<name>.dsp`. The Makefile finds it automatically and builds LV2, VST3 and CLAP plugins, with offline numerical tests.

`AGENTS.md` is the authority. This skill gives the working order, the commands, some design practice and the traps. If they ever disagree, `AGENTS.md` wins: say so, and fix the skill.

## Before you start

1. Read `AGENTS.md` (hard rules), `docs/development/designing-new-sounds.md` and, for anything with a nonlinearity or a level-dependent control, `docs/development/designing-for-feel.md`.
2. Pick the kind of effect. Prefer the first two:
   * **Original**: a sonic idea with no reference device. Needs `docs/<name>/design-notes.md`.
   * **Circuit-inspired**: starts from a real circuit and departs from it. Needs design notes, plus circuit notes for the borrowed part.
   * **Modelled**: a sourced model of one device. Needs `docs/<name>/circuit-notes.md`.
3. Choose a neutral `<name>` (lower case, no spaces). Never use a manufacturer’s or product’s name in a file name, `declare name`, UI label or URI. If hardware is referenced, add its manufacturer and product names to `tools/trademarks.txt`.
4. Check the toolchain with `faust --version` (2.88 was used; older versions are covered in `docs/install.md`) and `make help`. If something is missing, ask the user before installing anything. `make image` and `make container RUN="..."` give a ready toolchain in a container.
5. Optional: sketch the signal path in the browser effect designer (`docs/usage/designer.md`, blocks in `web/designer/blocks.js`). Its download is a rule-abiding starting point for `src/<name>.dsp`, but every constant it marks `// chosen in the designer` still needs notes, and the workflow below still applies.

## Hard rules (short form)

* **Clean-room.** Use public schematics, analyses, measurements and manuals only. Never decompile, copy or match against a proprietary plugin or firmware.
* **No trademarks** in `src/`, `tests/` or file names.
* **British English** in docs, comments and UI text (colour, behaviour, modelling, centre).
* **Every constant is labelled** documented, reported, inferred or chosen, with the intent of the chosen ones. Never guess silently.
* **You can’t listen.** Judge by measurement, and list what a human should tune by ear.
* **SPDX header** on every new file (code `MIT`, `docs/` `CC-BY-4.0`), or a `REUSE.toml` entry. Committed audio is FLAC. Schematics are KiCad `.kicad_sch`.
* **Ask first** before anything destructive or system-wide: `sudo`, package installs, deleting outside `build/` and `tests/out/`, or overwriting anything in `~/.lv2`, `~/.vst3` or `~/.clap` that this repo did not build.

## Design practice

Short reminders; the linked pages explain each one.

* **Design to a target.** Decide the harmonic profile, the response shape and the cleanup curve first, then find a structure that produces them. Targets become tests.
* **Shape before and after the clipper.** The filter in front sets which band distorts; the one after tames fizz. This tone shaping matters as much as the curve itself. Yeh’s thesis [1] analyses it in classic circuits.
* **Gain staging.** Aim for roughly unity loudness at the default settings, give each control a useful range across its whole travel (dB or log laws for gain and frequency), and compare settings loudness-matched with `loudness()`, since louder reads as better.
* **Bass keeps its fundamental.** Use `fi.dcblockerat(5)`, check the low B (31 Hz) and low E (41 Hz), and consider a clean low band or a dry blend under the drive.
* **Feel is state.** Cleanup, bloom, sag and recovery need memory. Split the stage into a smooth base-rate control and a memoryless shaper (`pk.oversample4c`, `pk.biasShift`, `pk.biased`), and make the control’s minimum identical to the effect without it. See `docs/development/designing-for-feel.md`.
* **Aliasing.** Oversample every nonlinearity and measure against `RENDER_1X`. Antiderivative antialiasing [2] is a possible future `pedalkit.lib` block; propose it rather than hand-rolling it in one effect.
* **Know the library’s limits.** Clipping inside an audio-rate feedback loop can’t be split into control and shaper, and `pedalkit.lib` has no solver for it yet. Say so in the open questions rather than approximating silently.
* **Unreadable sources.** If a page or paper can’t be fetched, say so in the notes, mark the values that depend on it as reported or inferred, and list it under open questions. The BassGrit and MidHump circuit notes show the form.

Further reading: the [Faust libraries reference](https://faustlibraries.grame.fr/), J. O. Smith’s [Introduction to Digital Filters](https://ccrma.stanford.edu/~jos/filters/) and [Physical Audio Signal Processing](https://ccrma.stanford.edu/~jos/pasp/), and the [DAFx paper archive](https://www.dafx.de/paper-archive/).

1. D. T. Yeh, [*Digital Implementation of Musical Distortion Circuits by Analysis and Simulation*](https://ccrma.stanford.edu/~dtyeh/papers/DavidYehThesisdoublesided.pdf), PhD dissertation, Stanford University, 2009.
2. J. D. Parker, V. Zavalishin and E. Le Bihan, “Reducing the aliasing of nonlinear waveshaping using continuous-time convolution”, *Proc. DAFx-16*, Brno, 2016 (in the [DAFx paper archive](https://www.dafx.de/paper-archive/)).

## Workflow

Work through these in order. Each step has a gate: don’t move on until it passes.

### 1. Notes first

Write the reasoning before any DSP. Outlines are in [references/templates.md](references/templates.md).

* Design notes: the idea, prior art, the block diagram (new against reused blocks), every constant with its confidence and intent, the **measurable targets**, **dynamics and feel** (how it responds to picking strength and over a note, as targets), open questions, numbered sources.
* Circuit notes: use `docs/bassdrive/circuit-notes.md` as the template.

Gate: every constant you intend to use appears in the notes with a confidence level.

### 2. DSP: `src/<name>.dsp`

`src/bassdrive.dsp` is the worked example; `src/midhump.dsp` shows a stateful control (Bloom). A skeleton is in [references/templates.md](references/templates.md).

* SPDX header, then a comment showing the signal flow.
* `declare name/description/author/license/version/lv2class`, and optionally `homepage`. The version starts at `0.1.0`. `lv2class` is an LV2 class without its prefix (`DistortionPlugin`, `DelayPlugin`, `FilterPlugin`); it also sets the VST3 subcategory and the CLAP feature.
* `import("stdfaust.lib"); pk = library("pedalkit.lib");`
* Reuse before writing: `pedalkit.lib` has `oversample4`/`oversample4c`, `asymTanh`, `softSat`, `kneeClip`, `asymSoftHard`, `biased`, `biasShift`, `tf2a`/`tf1a`, `lowShelf2`/`highShelf2` and `safety`. Signatures are in `docs/development/pedalkit-lib.md`.
* Sliders: `hslider("[n]Label [unit:dB] [tooltip:...]", default, min, max, step) : si.smoo`. Every control has a unit, range, default and smoothing. The `[n]` prefix fixes the order, and tests address sliders by label. After a release, append new controls rather than renumbering.
* Constants go at the top as named values, each with a source or intent comment.
* Every nonlinearity goes inside `pk.oversample4(f)`. `f` must be **memoryless**; filters go outside. Behaviour with memory goes in a base-rate control `c`, passed to `f(x, c)` with `pk.oversample4c(f)`.
* Analogue transfer functions with coefficients in rad/s go through `pk.tf2a`/`pk.tf1a`, not `fi.tf2s`.
* Any dry or parallel path that meets an oversampled path gets `@(pk.os4Latency)`, or the blend comb-filters.
* Report latency with the `hbargraph("Latency [unit:samples] [lv2:reportsLatency] [lv2:integer]", 0, 256)` pattern and `attach(_, latency)`, fed from the same named constant that delays the dry path. The budget is 128 samples; waveshapers with no filter between them share one `pk.oversample4`.
* Smooth switches as well as sliders: crossfade or glide, never jump.
* End `process` with `pk.safety(0.989)`.
* Reusable DSP belongs in `src/lib/pedalkit.lib`, documented in `AGENTS.md` and `docs/development/pedalkit-lib.md`. Don’t change an existing signature without updating every effect that uses it and running `make test` for all of them.

Gate: `make lv2 FX=<name>` compiles. `faust2lv2` prints spurious “bad port property 'unit:…'” messages; ignore them.

### 3. Tests: `tests/<name>/test_*.py`

Import helpers with `from fxtest import ...`; the full list is in `tests/lib/fxtest.py` and `docs/development/testing.md`. Copy the pattern from `tests/bassdrive/`. Each script starts with an SPDX header, prints its name and ends with `finish()`.

Minimum set:

* silence in gives silence out (`test_silence.py`)
* peak ≤ 0 dBFS at the extreme settings (`test_peak.py`)
* frequency response at several settings (`test_freqresp.py`)
* harmonic content (`test_harmonics.py`), with `RENDER` against `RENDER_1X` for aliasing whenever the effect oversamples
* for original or circuit-inspired effects, the **measurable targets from the design notes** (`tests/midhump/test_targets.py`)
* for behaviour over time or level, `pluck`, `burst`, `harmonics_over_time` and `harmonic_trajectory`, with the aliasing check repeated while the control is most active (`tests/midhump/test_dynamics.py`)

Save every plot with `save_plot(fig, name)` (SVG) and the numbers behind it with `write_csv(name, header, rows)` in long format. Write listening renders with `write_wav`.

`tests/common/` runs for every effect with no extra code: latency report and budget, zipper on every control, CPU per instance and on decaying tails, and recovery after a hot input. Fix the effect when one fails; the limits and the reasons for them are in `docs/development/feel-cpu-stability.md`. To time a change, use `bench(x, **params)` and compare `cpu.csv` with `main`.

Gate: `make lv2 lint test FX=<name>` passes. Open the SVGs in `tests/out/<name>/` (including `latency.svg` and `zipper.svg`) and read them before reporting.

### 4. Other formats

```sh
make vst3 pluginval FX=<name>
make clap clap-validate FX=<name>
```

Fix every failure. The first VST3 build clones the SDK into `build/`, and the first CLAP build clones the CLAP headers. Both need network access.

### 5. Presets (optional)

Write `src/<name>.presets.toml`, using `src/basspreamp.presets.toml` as the template. Set **every** control in every preset, because LV2 hosts leave unlisted controls where they were. Keys are UI labels. `tools/presets.py` builds the file into the LV2, VST3 and CLAP plugins alike. Say in the file that the settings are chosen. Add `tests/<name>/test_presets.py`, which renders each preset, checks its peak and loudness-matches it with `loudness()`.

### 6. Docs

* Add a row to the `README.md` effect table. Keep the README terse: the controls table and all other detail go in `docs/<name>/index.md`.
* Write `docs/<name>/index.md`, modelled on `docs/bassdrive/index.md`: the intro, a *Download* heading holding `<!-- downloads:<name> -->`, the property table, then controls, signal path, measured behaviour with plots from `../measurements/<name>/` and the CSV linked, what to tune by ear, and known limitations. An original effect opens with the idea.
* Add a row to the effect table in `docs/effects/index.md`, and a card to `docs/index.md` like the others: name and type, one plain-language sentence about the sound, `<!-- download-button:<name> -->`, and links to the effect page and `demo/index.html?fx=<name>`.
* Write `docs/<name>/changelog.md` with a `## [0.1.0]` section. The release workflow refuses a tag without one.
* Add the page, the notes and the changelog to `nav` in `mkdocs.yml`, under *Effects*.
* Required whenever there are circuit notes: write `tools/schematics/<name>.py` (start from the closest existing script), following `docs/development/schematics.md`. It draws the modelled circuit, one sub-sheet per section of the notes, with `Confidence` and `Source` fields on every part and `expect()` on every corner frequency and gain the notes quote. Run `make schematic-sources FX=<name>`, then `make schematic-check erc schematics FX=<name>`, read every sheet, never hand-edit the `.kicad_sch`, and embed the sheets in the circuit notes and the effect page.
* Run `make test web web-test schematics docs` (needs `pip install -r tools/docs-requirements.txt`, Node.js and npm; pass `MKDOCS=<path>` if MkDocs lives in a virtualenv). It builds with `--strict`, so fix every warning. The browser demo picks up the new effect without page changes.

### 7. Check and open the PR

```sh
make check     # pre-commit run --all-files
make format    # fixes Python lint and formatting if ruff complains
```

`make check` runs ruff, shellcheck, markdownlint, codespell (including British English), `reuse`, `no-trademarks`, `params-stable`, `schematics-present`, `effect-checklist` (`tools/check-effects.py`: declares, controls, latency, notes, docs pages and their contents, downloads placeholder, and minimum tests) and `faust-compile`. After `make test`, run `make check-outputs FX=<name>` to confirm every plot and CSV the docs link was written; CI also runs it for the plugins and schematics.

Then open a draft PR from a branch, following `.github/pull_request_template.md`: tick or justify every checklist item and fill in “What to listen for”. Add the `new-effect` and `effect: <name>` labels (create the latter). Never push to `main` or force-push.

## Common traps

| Symptom | Cause and fix |
|---|---|
| Blend sounds hollow or phasey | The dry path isn’t delayed by `@(pk.os4Latency)` |
| Oversampled output is wrong or noisy | `f` in `oversample4` has state (a filter or `mem`). Move it outside, or into a control passed with `oversample4c` |
| Aliasing appears only when a dynamic control moves | The control fed to `oversample4c` isn’t smooth enough. Lengthen its attack, or smooth after any saturation |
| Low E (41 Hz) or low B (31 Hz) loses weight | `fi.dcblocker` used instead of `fi.dcblockerat(5)` |
| An analogue filter lands at the wrong frequency | `fi.tf2s` used with coefficients in rad/s. Use `pk.tf2a`/`pk.tf1a` |
| A control such as `Gain=80` is ignored | The test’s label doesn’t match the slider label exactly |
| `lv2lint` fails on licence, version or class | A `declare license/version/lv2class` is missing or malformed. The version must be `major.minor.micro` |
| `libLLVM.so.NN` error from Faust | Partial system upgrade. The fix is `sudo pacman -Syu`, so ask the user |
| Faust “undefined symbol” | Faust is too old for a library function such as `fi.dcblockerat`. See `docs/install.md`, or use `make container` |
| Docs build fails under `--strict` | Broken link or missing `nav` entry. Run `make test web schematics` before `make docs` so the measurements, demo and sheets exist |
| Saved projects of a released effect load wrong values | Controls were reordered or the `.dsp` renamed. The VST3 class ID, CLAP ID and parameter order derive from them, so neither is allowed after release. The `params-stable` hook catches a moved, renamed or retyped control |
| `test_zipper.py` fails on a control | It has no `si.smoo`, or the smoothed value passes through something with steps (`int`, `ba.if`, a table) afterwards |
| `test_latency.py`: energy before the reported latency | A dry or parallel path skips `@(pk.os4Latency)`, or the bargraph reports more than the path delays |
| `test_latency.py`: strongest tap too late | The bargraph leaves out an oversampler stage. Feed it and the dry-path delay from one constant |
| `test_cpu.py`: the tail costs more than live signal | Subnormal state. Check the build still passes `FAUSTFLAGS` (`-ftz 1`) to Faust |

## Reporting back

End with a short summary:

* what works, backed by test results (quote the numbers)
* what is approximate, referring to the *chosen* constants
* what the user should check by listening, naming the constant or control to adjust
