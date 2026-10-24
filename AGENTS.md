# AGENTS.md: working on this repository

This file is for coding agents (and humans) adding or changing effects here. Read it before touching anything. `README.md` covers users, building and hosts.

## What this repo is

A collection of Faust effects, each built as a native Linux LV2 plugin and a VST3 plugin, with offline numerical tests. One effect is one `src/<name>.dsp`. The Makefile discovers effects automatically. Shared DSP lives in `src/lib/pedalkit.lib` (import it as `pk = library("pedalkit.lib");`).

## Hard rules

1. **Clean-room only.** Work from public schematics, circuit analyses, measurements, reviews and manuals. Never decompile, disassemble or copy a proprietary plugin, binary or firmware, and don't use one as a "reference" to match against.
2. **No trademarks.** Plugin names, `declare name`, UI labels, URIs and file names must be neutral. In the docs, a manufacturer's product name may appear *only* to identify the reference hardware, never as branding. The `no-trademarks` pre-commit hook checks file names, `src/` and `tests/` against `tools/trademarks.txt`.
3. **British English** in all documentation, comments and UI text: colour, behaviour, modelling, analyse, centre.
4. **Say when you're unsure.** Every circuit value in the DSP is documented, reported, inferred or chosen. The circuit notes must say which, with a link for anything sourced. Never guess silently.
5. **Ask the user before anything destructive or system-wide.** That includes `sudo`, package installs, deleting outside `build/` and `tests/out/`, and overwriting their `~/.lv2` or `~/.vst3` contents other than this repo's own bundles.
6. **You can't listen.** Judge sound by measurement (harmonics, frequency response, aliasing, levels), describe it in those terms, and list the parameters a human should tune by ear.
7. **Open formats and machine-readable licensing.** Every new file has an SPDX header (`SPDX-FileCopyrightText` and `SPDX-License-Identifier`), or an entry in `REUSE.toml` if it can't take comments. Code is `MIT` and `docs/` is `CC-BY-4.0`. The `reuse` pre-commit hook enforces this. Any audio that gets committed is FLAC. Schematics are KiCad `.kicad_sch`, redrawn from the sources rather than copied as images, because a third party's drawing has its own copyright.

## Adding a new effect `<name>`

1. **Research first.** Write `docs/<name>/circuit-notes.md`:
   - documented controls and specs
   - the block diagram
   - each stage with component values and the corner frequencies derived from them
   - the confidence level for each claim
   - a numbered source list with links
   - open questions

   Use `docs/bassdrive/circuit-notes.md` as the template. `REUSE.toml` already licenses everything under `docs/` as CC-BY-4.0.

   Add the reference hardware's manufacturer and product names to `tools/trademarks.txt` if they aren't there yet, so the `no-trademarks` hook keeps them out of the plugin.
2. **DSP.** Write `src/<name>.dsp`:
   - `declare name/description/author/license/version/lv2class`. The LV2 and VST3 plugins take their name from `declare name`, and the VST3 subcategory comes from `lv2class`. `license` is an SPDX identifier (e.g. `MIT`), `version` is `major.minor.micro`, and `lv2class` is an LV2 plugin class without its prefix (e.g. `DistortionPlugin`, `DelayPlugin`, `FilterPlugin`). `tools/fix-ttl.py` turns these into the LV2 metadata `lv2lint` requires. An optional `declare homepage "https://…"` adds the maintainer's homepage.
   - If the effect adds latency (e.g. via `pk.oversample4`), report it: attach `hbargraph("Latency [unit:samples] [lv2:reportsLatency] [lv2:integer]", 0, 256)` fed with the delay, as `src/bassdrive.dsp` does.
   - Sliders: `hslider("[n]Label [unit:dB] [tooltip:...]", default, min, max, step) : si.smoo`. Every control gets a unit, a sensible range and default, and smoothing. The `[n]` prefix fixes the order. Test scripts address sliders by their label, e.g. `Gain=80`.
   - Put the circuit constants at the top as named values, each with a comment saying where it came from.
   - Put every nonlinearity inside `pk.oversample4(f)`. `f` **must be memoryless** (a pure waveshaper), because it is applied to four parallel phase streams. Filters belong outside it.
   - Any dry or parallel path that meets an oversampled path must be delayed by `@(pk.os4Latency)`, or the blend will comb-filter.
   - Use `fi.dcblockerat(5)` (5 Hz), not `fi.dcblocker` (about 35 Hz), on anything meant for bass.
   - End `process` with `pk.safety(0.989)` so no sample can exceed 0 dBFS.
   - Comment the signal flow at the top of the file.
3. **Tests.** Add `tests/<name>/test_*.py`:
   - Each script does `from fxtest import ...` (`tests/lib/fxtest.py` provides `render`, `sine`, `log_sweep`, `transfer`, `harmonics`, `write_wav`, `save_plot`, `write_csv`, `check`, `finish`, `plt`, `SR`, `OUT`).
   - Each script ends with `finish()`, which exits non-zero on any failed `check`.
   - The minimum set is silence in gives silence out, peak ≤ 0 dBFS at the extreme settings, frequency response at several settings, and harmonic content. Add an aliasing comparison (`RENDER` against `RENDER_1X`) whenever the effect oversamples.
   - Write results to `OUT` (`tests/out/<name>/`) in open formats. Save plots as SVG with `save_plot(fig, name)`. Save the numbers behind every plot as CSV with `write_csv(name, header, rows)`, one row per data point in long format, so others can reuse them without reading values off an image. Use WAV via `write_wav` for listening renders.
4. **Build and check:** `make lv2 lint test FX=<name>`, `make vst3 pluginval FX=<name>`, then `pre-commit run --all-files`. Fix every `lv2lint`, VST3 validator, pluginval and pre-commit failure. Read the plots before reporting results. CI runs both on every push and pull request.
5. **Docs.** Add a row to the README's effect table and a controls table for the effect. On the documentation site (`docs/`, published to GitHub Pages):
   - add `docs/<name>/index.md`, modelled on `docs/bassdrive/index.md`: controls, signal path, measured behaviour with the plots embedded from `../measurements/<name>/` and the CSV linked, what to tune by ear, and known limitations
   - add a row to the effect tables in `docs/index.md` and `docs/effects/index.md`
   - add the page and the circuit notes to `nav` in `mkdocs.yml`, under *Effects*
   - run `make test docs` (tools: `pip install -r tools/docs-requirements.txt`). It builds with `--strict`, so fix every warning.

## Shared library (`src/lib/pedalkit.lib`)

| Function | Purpose |
|---|---|
| `oversample4(f)` / `oversample1(f)` | 4x polyphase oversampling around memoryless `f` (129-tap windowed sinc) / pass-through for A/B |
| `os4Latency` | 32: base-rate delay of `oversample4` |
| `asymTanh(pos, neg)` | Asymmetric tanh clipper (generates even-order harmonics) |
| `softSat(v)` | Symmetric tanh saturation at ±v |
| `kneeClip(a, n)` | Clipper with adjustable hardness n, limiting at ±a |
| `asymSoftHard(pos, neg, n)` | Soft tanh above zero, harder knee below; even harmonics grow with drive |
| `safety(lim)` | Transparent-below-90 % soft limiter that never exceeds `lim` |

When you add something reusable, put it here rather than copying it into an effect, and document it in this table and in `docs/development/pedalkit-lib.md`. Don't change existing signatures without updating every effect that uses them, and rerun `make test` across all effects.

## Build mechanics

- `make` targets: `lv2`, `vst3`, `standalone`, `lint`, `pluginval`, `test`, `describe`, `install`, `install-vst3`, `uninstall`, `clean`. All of them take `FX=<name>`, and the default is every effect. `docs` and `docs-serve` build and preview the MkDocs site (`mkdocs.yml`) into `build/site/`; pass `MKDOCS=<path>` if `mkdocs` is in a virtual environment.
- `tools/mkdocs_hooks.py` publishes `tests/out/<name>/*.svg` and `*.csv` on the site as `measurements/<name>/`, so run `make test` before `make docs`. `.github/workflows/docs.yml` does both and deploys to GitHub Pages from `main`.
- `faust2lv2` and `faust2jaqt` build in the current directory, so each effect is staged in `build/<name>/`, with `src/lib/*.lib` copied next to the `.dsp`. The bundle ends up in `build/<name>.lv2`.
- Plugin URI: `urn:pedalkit/<name>`.
- After `faust2lv2`, the Makefile runs `tools/fix-ttl.py` on the bundle's TTL. `faust2lv2` writes the licence as a string, and has no way to express `lv2:minorVersion`/`microVersion` or a plugin class. Without the script, `lv2lint` fails.
- `faust2lv2` prints spurious "bad port property 'unit:…'" messages. These are a quirk of its template and can be ignored.
- `faust2lv2` needs the Boost headers (`boost` on Arch, `libboost-dev` on Debian), even for effects that use no MIDI.
- Tests use a separate renderer, `build/<name>/render`, built from `tests/lib/render-arch.cpp`. It reads and writes raw float32 on stdin and stdout, takes `Label=value` arguments, and pre-rolls 2 s of silence so the smoothers settle. `render_1x` is the same DSP with `oversample4(` replaced by `oversample1(`.
- **VST3.** No Faust script builds VST3: `faust2vst`, `faust2w64vst` and `faust2faustvst` are VST2, and `faust2juce` goes through JUCE (AGPL/commercial). So the repo has its own architecture, `tools/vst3/faust-vst3.cpp`, written against the MIT VST3 SDK.
  - It is a `SingleComponentEffect` with no custom GUI. Each Faust control becomes a parameter, numbered in UI order. A bargraph tagged `[lv2:reportsLatency]` becomes `getLatencySamples()`. Subnormals are flushed to zero during `process()`.
  - `make vst3` compiles the `.dsp` into that architecture. `tools/vst3-meta.py` writes `plugin_meta.h` (name, vendor, version, homepage, subcategory, class ID) from the `declare`s, and `tools/vst3/CMakeLists.txt` builds `build/<name>.vst3` with the SDK's `smtg_add_vst3plugin`.
  - The SDK is cloned at a pinned tag (`VST3_SDK_TAG` in the Makefile) into `build/vst3sdk`. Its CMake is configured so that it never symlinks into `~/.vst3`, and so that Steinberg's validator runs on every bundle as a post-build step.
  - `make pluginval` then runs pluginval at strictness 10.
- **VST3 class ID** is `uuid5(NAMESPACE_DNS, "pedalkit.<name>")`, which matches the LV2 URI `urn:pedalkit/<name>`. Hosts save it in projects, so it must never change for a released effect: don't rename a released `.dsp`, and don't change the derivation.
- **VST3 parameter IDs and saved state** follow the order of the controls (the `[n]` prefixes). Append new controls at the end rather than renumbering, or existing projects will load the wrong values.
- `make describe` writes a format-neutral description of each effect: `faust -json` gives `build/<name>/<name>.dsp.json` (every control's label, unit, range and default), and `faust -svg` gives the block diagram in `build/<name>/<name>-svg/`. CI uploads both as the `describe` artifact.
- Generated files only ever go in `build/` and `tests/out/`. Never commit them.

## Issue labels

The issue forms in `.github/ISSUE_TEMPLATE/` apply labels automatically. Triage with these:

- **Type:** `bug`, `enhancement`, `new-effect`, `modelling`, `documentation`, `question`.
- **Area:** `area: dsp`, `area: library`, `area: tests`, `area: build`, `area: ci`, `area: circuit-notes`.
- **Effect:** `effect: <name>`, one per effect. Create it when you add the effect.
- **Repo rules:** `licensing`, `clean-room`, `needs-sources` (unsourced or low-confidence circuit value), `needs-listening` (needs a human ear), `aliasing` (oversampling or latency).
- **Triage:** `needs-info`, `duplicate`, `wontfix`, `help wanted`, `good first issue`.
- **Bots:** `dependencies` and `github_actions` come from Dependabot.

## Environment notes

- Arch-based machine (Omarchy). Faust links against the system LLVM. A `libLLVM.so.NN` error means a partial upgrade, and the fix is `sudo pacman -Syu`, which needs the user's approval.
- The audio server is PipeWire with `pipewire-jack`, so JACK builds run without a separate JACK daemon.

## Reporting back

Finish any piece of work with a short summary covering:

- what works, backed by test results
- what is approximate, with references to the "chosen" values
- what the user should check by listening, naming the constant or control to adjust
