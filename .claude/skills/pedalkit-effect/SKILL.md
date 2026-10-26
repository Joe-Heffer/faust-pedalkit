---
name: pedalkit-effect
description: Design, build, test and document a new guitar or bass effect plugin (LV2, VST3, CLAP) in this Faust Pedal Kit repository. Use when asked to add, prototype or modify an effect, write a src/<name>.dsp, add pedalkit.lib blocks, write design or circuit notes, add effect tests or presets, or open a PR for an effect.
---

# Pedal Kit: creating an effect

This repository is a workshop for new guitar and bass effects written in Faust. One effect is one `src/<name>.dsp`. The Makefile finds it automatically and builds LV2, VST3 and CLAP plugins, with offline numerical tests.

`AGENTS.md` is the authority. This skill gives the working order, the commands and the traps. If they ever disagree, `AGENTS.md` wins: say so, and fix the skill.

## Before you start

1. Read `AGENTS.md` (hard rules) and `docs/development/designing-new-sounds.md`.
2. Pick the kind of effect. Prefer the first two:
   - **Original**: a sonic idea with no reference device. Needs `docs/<name>/design-notes.md`.
   - **Circuit-inspired**: starts from a real circuit and departs from it. Needs design notes, plus circuit notes for the borrowed part.
   - **Modelled**: a sourced model of one device. Needs `docs/<name>/circuit-notes.md`.
3. Choose a neutral `<name>` (lower case, no spaces). Never use a manufacturer's or product's name in a file name, `declare name`, UI label or URI. If hardware is referenced, add its manufacturer and product names to `tools/trademarks.txt`.
4. Check the toolchain with `faust --version` (2.88 was used) and `make help`. If something is missing, ask the user before installing anything. `make image` and `make container RUN="..."` give a ready toolchain in a container.

## Hard rules (short form)

- **Clean-room.** Use public schematics, analyses, measurements and manuals only. Never decompile, copy or "match against" a proprietary plugin or firmware.
- **No trademarks** in `src/`, `tests/` or file names.
- **British English** in docs, comments and UI text (colour, behaviour, modelling, centre).
- **Every constant is labelled** documented, reported, inferred or chosen, with the intent of the chosen ones. Never guess silently.
- **You can't listen.** Judge by measurement, and list what a human should tune by ear.
- **SPDX header** on every new file (code `MIT`, `docs/` `CC-BY-4.0`), or a `REUSE.toml` entry. Committed audio is FLAC. Schematics are KiCad `.kicad_sch`.
- **Ask first** before anything destructive or system-wide: `sudo`, package installs, deleting outside `build/` and `tests/out/`, or overwriting anything in `~/.lv2`, `~/.vst3` or `~/.clap` that this repo did not build.

## Workflow

Work through these in order. Each step has a gate: don't move on until it passes.

### 1. Notes first

Write the reasoning before any DSP. Outlines are in [references/templates.md](references/templates.md).

- Design notes: the idea, the block diagram (new against reused blocks), every constant with its confidence and intent, the **measurable targets**, numbered sources, open questions.
- Circuit notes: use `docs/bassdrive/circuit-notes.md` as the template.

Gate: every constant you intend to use appears in the notes with a confidence level.

### 2. DSP: `src/<name>.dsp`

`src/bassdrive.dsp` is the worked example. A skeleton is in [references/templates.md](references/templates.md).

- SPDX header, then a comment showing the signal flow.
- `declare name/description/author/license/version/lv2class`, and optionally `homepage`. The version starts at `0.1.0`. `lv2class` is an LV2 class without its prefix (`DistortionPlugin`, `DelayPlugin`, `FilterPlugin`); it also sets the VST3 subcategory and the CLAP feature.
- `import("stdfaust.lib"); pk = library("pedalkit.lib");`
- Sliders: `hslider("[n]Label [unit:dB] [tooltip:...]", default, min, max, step) : si.smoo`. Every control has a unit, range, default and smoothing. The `[n]` prefix fixes the order, and tests address sliders by label. After a release, append new controls rather than renumbering.
- Constants go at the top as named values, each with a source or intent comment.
- Every nonlinearity goes inside `pk.oversample4(f)`. `f` must be **memoryless**; filters go outside.
- Any dry or parallel path that meets an oversampled path gets `@(pk.os4Latency)`, or the blend comb-filters.
- Report latency with the `hbargraph("Latency [unit:samples] [lv2:reportsLatency] [lv2:integer]", 0, 256)` pattern and `attach(_, latency)`.
- Use `fi.dcblockerat(5)`, not `fi.dcblocker`, for anything meant for bass.
- End `process` with `pk.safety(0.989)`.
- Reusable DSP belongs in `src/lib/pedalkit.lib`, documented in `AGENTS.md` and `docs/development/pedalkit-lib.md`. Don't change an existing signature without updating every effect that uses it and running `make test` for all of them.

Gate: `make lv2 FX=<name>` compiles. `faust2lv2` prints spurious "bad port property 'unit:…'" messages; ignore them.

### 3. Tests: `tests/<name>/test_*.py`

Import helpers with `from fxtest import ...`: `render`, `sine`, `log_sweep`, `transfer`, `harmonics`, `db`, `write_wav`, `save_plot`, `write_csv`, `check`, `finish`, `loudness`, `presets`, `plt`, `SR`, `OUT`, `RENDER`, `RENDER_1X`. Copy the pattern from `tests/bassdrive/`. Each script starts with an SPDX header, prints its name and ends with `finish()`.

Minimum set:

- silence in gives silence out
- peak ≤ 0 dBFS at the extreme settings
- frequency response at several settings
- harmonic content
- `RENDER` against `RENDER_1X` for aliasing, whenever the effect oversamples
- for original or circuit-inspired effects, the **measurable targets from the design notes**, since those show the idea works

Save every plot with `save_plot(fig, name)` (SVG) and the numbers behind it with `write_csv(name, header, rows)` in long format. Write listening renders with `write_wav`.

Gate: `make lv2 lint test FX=<name>` passes. Open the SVGs in `tests/out/<name>/` and read them before reporting.

### 4. Other formats

```sh
make vst3 pluginval FX=<name>
make clap clap-validate FX=<name>
```

Fix every failure. The first VST3 build clones the SDK into `build/`, and the first CLAP build clones the CLAP headers. Both need network access.

### 5. Presets (optional)

Write `src/<name>.presets.toml`, using `src/basspreamp.presets.toml` as the template. Set **every** control in every preset, because LV2 hosts leave unlisted controls where they were. Keys are UI labels. `tools/presets.py` builds the file into the LV2, VST3 and CLAP plugins alike. Say in the file that the settings are chosen. Add `tests/<name>/test_presets.py`, which renders each preset, checks its peak and loudness-matches it with `loudness()`.

### 6. Docs

- Add a row to the `README.md` effect table, with a controls table. Keep the README terse and put the detail in `docs/<name>/index.md`.
- Write `docs/<name>/index.md`, modelled on `docs/bassdrive/index.md`: controls, signal path, measured behaviour with plots from `../measurements/<name>/` and the CSV linked, what to tune by ear, and known limitations. An original effect opens with the idea.
- Add rows to the effect tables in `docs/index.md` and `docs/effects/index.md`.
- Write `docs/<name>/changelog.md` with a `## [0.1.0]` section. The release workflow refuses a tag without one.
- Add the pages to `nav` in `mkdocs.yml`, under *Effects*.
- Optional: draw the borrowed circuit in KiCad as `docs/<name>/schematics/<name>.kicad_sch`, one sub-sheet per stage, following `docs/development/schematics.md`, and run `make erc schematics FX=<name>`.
- Run `make test web schematics docs` (needs `pip install -r tools/docs-requirements.txt`; pass `MKDOCS=<path>` if it lives in a virtualenv). It builds with `--strict`, so fix every warning.

### 7. Check and open the PR

```sh
make check     # pre-commit run --all-files
make format    # fixes Python lint and formatting if ruff complains
```

`make check` runs ruff, shellcheck, markdownlint, codespell (including British English), `reuse`, `no-trademarks` and `faust-compile`.

Then open a draft PR from a branch, following `.github/pull_request_template.md`: tick or justify every checklist item and fill in "What to listen for". Never push to `main` or force-push.

## Common traps

| Symptom | Cause and fix |
|---|---|
| Blend sounds hollow or phasey | The dry path isn't delayed by `@(pk.os4Latency)` |
| Oversampled output is wrong or noisy | `f` in `oversample4` has state (a filter or `mem`). Move it outside |
| Low E (41 Hz) or low B (31 Hz) loses weight | `fi.dcblocker` used instead of `fi.dcblockerat(5)` |
| A control such as `Gain=80` is ignored | The test's label doesn't match the slider label exactly |
| `lv2lint` fails on licence, version or class | A `declare license/version/lv2class` is missing or malformed. The version must be `major.minor.micro` |
| `libLLVM.so.NN` error from Faust | Partial system upgrade. The fix is `sudo pacman -Syu`, so ask the user |
| Faust "undefined symbol" | Faust is too old for a library function such as `fi.dcblockerat`. See the README |
| Docs build fails under `--strict` | Broken link or missing `nav` entry. Run `make test` before `make docs` so the measurements exist |
| Saved projects of a released effect load wrong values | Controls were reordered or the `.dsp` renamed. The VST3 class ID, CLAP ID and parameter order derive from them, so neither is allowed after release |

## Reporting back

End with a short summary:

- what works, backed by test results (quote the numbers)
- what is approximate, referring to the *chosen* constants
- what the user should check by listening, naming the constant or control to adjust
