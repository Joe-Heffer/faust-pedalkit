# AGENTS.md: working on this repository

This file is for coding agents (and humans) adding or changing effects here. Read it before touching anything. `README.md` covers users, building and hosts.

## What this repo is

A workshop for designing new guitar and bass effects in Faust, each built as a native Linux LV2, VST3 and CLAP plugin, with offline numerical tests. One effect is one `src/<name>.dsp`. The Makefile discovers effects automatically. Shared DSP lives in `src/lib/pedalkit.lib` (import it as `pk = library("pedalkit.lib");`).

The aim is new sounds and new kinds of effect, not copies of existing products. Modelling classic hardware is still useful, but as a means: to learn how a circuit gets its character, to calibrate the measurement tools, and to collect building blocks that original designs can reuse, bend and recombine. An effect here is one of:

- **Original:** a sonic idea with no single reference device. Its reasoning lives in `docs/<name>/design-notes.md`.
- **Circuit-inspired:** starts from a real circuit and deliberately departs from it (extra controls, impossible component values, stages a pedal could not have). It has design notes, plus circuit notes for the part it borrows.
- **Modelled:** a measured, sourced model of one piece of hardware, documented in `docs/<name>/circuit-notes.md`. BassDrive and BassPreamp are the existing examples.

Prefer the first two when you have the choice. When you build a model, say what it makes possible that the hardware does not, and move what is reusable into `pedalkit.lib`.

## Hard rules

1. **Clean-room only.** Anything taken from existing hardware or software comes from public schematics, circuit analyses, measurements, reviews and manuals. Never decompile, disassemble or copy a proprietary plugin, binary or firmware, and don't use one as a "reference" to match against. This applies to original designs too: invent, don't imitate a commercial plugin.
2. **No trademarks.** Plugin names, `declare name`, UI labels, URIs and file names must be neutral. In the docs, a manufacturer's product name may appear *only* to identify reference or inspiring hardware, never as branding. The `no-trademarks` pre-commit hook checks file names, `src/` and `tests/` against `tools/trademarks.txt`.
3. **British English** in all documentation, comments and UI text: colour, behaviour, modelling, analyse, centre.
4. **Say when you're unsure, and say why a value is what it is.** Every constant in the DSP is documented, reported, inferred or chosen. The design or circuit notes must say which, with a link for anything sourced and the intent behind anything chosen. In an original design most values are chosen, and that's fine as long as the notes say what each one is for. Never guess silently.
5. **Ask the user before anything destructive or system-wide.** That includes `sudo`, package installs, deleting outside `build/` and `tests/out/`, and overwriting their `~/.lv2`, `~/.vst3` or `~/.clap` contents other than this repo's own bundles.
6. **You can't listen.** Judge sound by measurement (harmonics, frequency response, aliasing, levels), describe it in those terms, and list the parameters a human should tune by ear.
7. **Open formats and machine-readable licensing.** Every new file has an SPDX header (`SPDX-FileCopyrightText` and `SPDX-License-Identifier`), or an entry in `REUSE.toml` if it can't take comments. Code is `MIT` and `docs/` is `CC-BY-4.0`. The `reuse` pre-commit hook enforces this. Any audio that gets committed is FLAC. Schematics are KiCad `.kicad_sch`, redrawn from the sources rather than copied as images, because a third party's drawing has its own copyright.

## Adding a new effect `<name>`

1. **Notes first.** Write the reasoning down before any DSP. `REUSE.toml` already licenses everything under `docs/` as CC-BY-4.0.
   - **Original or circuit-inspired effects:** write `docs/<name>/design-notes.md`, following the outline in `docs/development/designing-new-sounds.md`:
     - the sonic idea: what it should sound like and what a player gets that existing effects don't give them
     - the block diagram, and which blocks are new and which are reused (from `pedalkit.lib` or another effect)
     - each block's constants, with the confidence level and intent of each
     - the measurable targets that will show the idea works (a harmonic profile, a response shape, a modulation depth)
     - prior art and inspirations, with links, as a numbered source list
     - open questions, especially the ones only listening can answer
   - **Modelled effects, or the borrowed part of a circuit-inspired one:** write `docs/<name>/circuit-notes.md`, using `docs/bassdrive/circuit-notes.md` as the template:
     - documented controls and specs
     - the block diagram
     - each stage with component values and the corner frequencies derived from them
     - the confidence level for each claim
     - a numbered source list with links
     - open questions

   If any hardware is referenced, add its manufacturer and product names to `tools/trademarks.txt` if they aren't there yet, so the `no-trademarks` hook keeps them out of the plugin.
2. **DSP.** Write `src/<name>.dsp`:
   - `declare name/description/author/license/version/lv2class`. The LV2, VST3 and CLAP plugins take their name from `declare name`, and the VST3 subcategory and CLAP feature come from `lv2class`. `license` is an SPDX identifier (e.g. `MIT`), `version` is `major.minor.micro` and starts at `0.1.0` for every new effect (each effect is versioned and released on its own), and `lv2class` is an LV2 plugin class without its prefix (e.g. `DistortionPlugin`, `DelayPlugin`, `FilterPlugin`). `tools/fix-ttl.py` turns these into the LV2 metadata `lv2lint` requires. An optional `declare homepage "https://…"` adds the maintainer's homepage.
   - If the effect adds latency (e.g. via `pk.oversample4`), report it: attach `hbargraph("Latency [unit:samples] [lv2:reportsLatency] [lv2:integer]", 0, 256)` fed with the delay, as `src/bassdrive.dsp` does.
   - Sliders: `hslider("[n]Label [unit:dB] [tooltip:...]", default, min, max, step) : si.smoo`. Every control gets a unit, a sensible range and default, and smoothing. The `[n]` prefix fixes the order. Test scripts address sliders by their label, e.g. `Gain=80`.
   - Put the constants (circuit values and design choices alike) at the top as named values, each with a comment saying where it came from or what it is for.
   - Put every nonlinearity inside `pk.oversample4(f)`. `f` **must be memoryless** (a pure waveshaper), because it is applied to four parallel phase streams. Filters belong outside it.
   - Any dry or parallel path that meets an oversampled path must be delayed by `@(pk.os4Latency)`, or the blend will comb-filter.
   - Use `fi.dcblockerat(5)` (5 Hz), not `fi.dcblocker` (about 35 Hz), on anything meant for bass.
   - End `process` with `pk.safety(0.989)` so no sample can exceed 0 dBFS.
   - Comment the signal flow at the top of the file.
3. **Tests.** Add `tests/<name>/test_*.py`:
   - Each script does `from fxtest import ...` (`tests/lib/fxtest.py` provides `render`, `sine`, `log_sweep`, `transfer`, `harmonics`, `write_wav`, `save_plot`, `write_csv`, `check`, `finish`, `loudness`, `presets`, `plt`, `SR`, `OUT`).
   - Each script ends with `finish()`, which exits non-zero on any failed `check`.
   - The minimum set is silence in gives silence out, peak ≤ 0 dBFS at the extreme settings, frequency response at several settings, and harmonic content. Add an aliasing comparison (`RENDER` against `RENDER_1X`) whenever the effect oversamples.
   - For an original or circuit-inspired effect, also test the measurable targets from the design notes, so the idea itself is checked, not just its safety.
   - Write results to `OUT` (`tests/out/<name>/`) in open formats. Save plots as SVG with `save_plot(fig, name)`. Save the numbers behind every plot as CSV with `write_csv(name, header, rows)`, one row per data point in long format, so others can reuse them without reading values off an image. Use WAV via `write_wav` for listening renders.
4. **Build and check:** `make lv2 lint test FX=<name>`, `make vst3 pluginval FX=<name>`, `make clap clap-validate FX=<name>`, then `make check` (`pre-commit run --all-files`). Fix every `lv2lint`, VST3 validator, pluginval, clap-validator and pre-commit failure. Read the plots before reporting results. CI runs both on every push and pull request.
5. **Docs.** Add a row to the README's effect table and a controls table for the effect. On the documentation site (`docs/`, published to GitHub Pages):
   - add `docs/<name>/index.md`, modelled on `docs/bassdrive/index.md`: controls, signal path, measured behaviour with the plots embedded from `../measurements/<name>/` and the CSV linked, what to tune by ear, and known limitations. For an original effect, open with the idea and the sound it is after rather than a reference device.
   - add a row to the effect tables in `docs/index.md` and `docs/effects/index.md`
   - add `docs/<name>/changelog.md`, modelled on `docs/bassdrive/changelog.md`, with a `## [0.1.0]` section; the release workflow refuses a tag whose version has no section there
   - add the page, the design and/or circuit notes and the changelog to `nav` in `mkdocs.yml`, under *Effects*
   - run `make test docs` (tools: `pip install -r tools/docs-requirements.txt`). It builds with `--strict`, so fix every warning.
6. **Presets (optional).** Add `src/<name>.presets.toml`, using `src/basspreamp.presets.toml` as the template: a list of `[[preset]]` tables with a `name`, a `comment` and a `controls` table keyed by UI label. Set every control, because LV2 hosts leave unlisted controls where they were. Treat the settings as chosen values and say so in the file. Add a `tests/<name>/test_presets.py` that renders each preset, checks its peak and loudness-matches it with `loudness()`, and list the presets in the README and on the effect's docs page.

## Shared library (`src/lib/pedalkit.lib`)

| Function | Purpose |
|---|---|
| `oversample4(f)` / `oversample1(f)` | 4x polyphase oversampling around memoryless `f` (129-tap windowed sinc) / pass-through for A/B |
| `os4Latency` | 32: base-rate delay of `oversample4` |
| `asymTanh(pos, neg)` | Asymmetric tanh clipper (generates even-order harmonics) |
| `softSat(v)` | Symmetric tanh saturation at ±v |
| `kneeClip(a, n)` | Clipper with adjustable hardness n, limiting at ±a |
| `asymSoftHard(pos, neg, n)` | Soft tanh above zero, harder knee below; even harmonics grow with drive |
| `tf2a(b2,b1,b0,a1,a0,w)` / `tf1a(b1,b0,a0,w)` | Analogue 2nd/1st-order section with coefficients in rad/s (as from a circuit analysis), bilinear-transformed with prewarp at `w`. `fi.tf2s` expects s normalised to `w`, so use these instead. |
| `safety(lim)` | Transparent-below-90 % soft limiter that never exceeds `lim` |

When you add something reusable, put it here rather than copying it into an effect, and document it in this table and in `docs/development/pedalkit-lib.md`. Don't change existing signatures without updating every effect that uses them, and rerun `make test` across all effects.

## Build mechanics

- `make` targets: `lv2`, `vst3`, `clap`, `standalone`, `lint`, `pluginval`, `clap-validate`, `test`, `describe`, `dist`, `install`, `install-vst3`, `install-clap`, `uninstall`, `clean`, `image`, `container`. All of them take `FX=<name>`, and the default is every effect. An unknown name stops `make` with the list of effects. `make help` lists the targets.
- `make check` runs `pre-commit run --all-files`, as CI does. `make format` fixes Python lint and formatting with the ruff that `.pre-commit-config.yaml` pins, so no separate ruff install is needed; it fails only if ruff leaves something it cannot fix.
- `make clean` removes `build/` and `tests/out/` but keeps the VST3 SDK clone in `build/vst3sdk`. `make distclean` removes that too. `docs` and `docs-serve` build and preview the MkDocs site (`mkdocs.yml`) into `build/site/`; pass `MKDOCS=<path>` if `mkdocs` is in a virtual environment.
- **Toolchain image.** `Dockerfile` defines the build and test toolchain: Faust, lv2lint, Boost, numpy and matplotlib, plus cmake, git and pluginval for VST3. `make image` builds it and `make container RUN="<targets>"` runs `make` inside it with the repository mounted at `/src`. The `build-test` and `vst3` CI jobs use the same image, so a new dependency goes in the `Dockerfile`, not in `ci.yml`. Package versions come from the Arch Linux Archive date `ARCH_SNAPSHOT`, which you bump by hand to move to a newer Faust. Dependabot bumps the base image digest. `make image DOCKERFILE=<file>` builds another Dockerfile.
- **Releases.** Each effect is released on its own, at its `declare version`. `make dist` packs, for each effect in `FX`, its LV2, VST3 and CLAP plugins, `tools/release/install.sh`, `tools/release/README.txt`, `LICENSE` and `docs/<name>/changelog.md` (as `CHANGELOG.md`) into `build/dist/<name>-<version>-linux-<arch>.tar.gz`, with one `SHA256SUMS` for them all.
  - Release binaries come from `Dockerfile.release` (Debian 12, Faust built from source at `FAUST_VERSION`), not the Arch image, whose newer glibc would stop the plugins loading on Ubuntu and Debian. It sets `LDFLAGS="-static-libgcc"` (not `-static-libstdc++`: Debian 12's static libstdc++ needs glibc 2.36), and the Makefile passes `LDFLAGS` to every plugin link line (faust2lv2, the VST3 CMake build and the CLAP link). Keep `FAUST_VERSION` in step with the Faust that `ARCH_SNAPSHOT` installs.
  - `.github/workflows/release.yml` runs on `<name>-vX.Y.Z` tags (e.g. `bassdrive-v0.1.0`). `tools/release/release-info.py` checks that the tag names an effect, equals its `declare version` and has a `## [X.Y.Z]` section in `docs/<name>/changelog.md`. The workflow builds that effect's tarball in that image, then checks it with `tools/release/check-portable.sh` on stock Ubuntu 22.04, runs lv2lint, pluginval and clap-validator on the shipped plugins in the Arch image, tests `install.sh`, and creates a **draft** GitHub release, titled from `declare name`, with the changelog section as its notes. A manual or pull-request run builds and checks every effect's tarball. Steps are in `docs/development/releasing.md`.
  - `install.sh` only touches the bundles it ships, in `~/.lv2`, `~/.vst3` and `~/.clap` (overridable by `LV2DIR`, `VST3DIR`, `CLAPDIR`). Keep it POSIX `sh` with no root.
- `tools/mkdocs_hooks.py` publishes `tests/out/<name>/*.svg` and `*.csv` on the site as `measurements/<name>/`, so run `make test` before `make docs`. `.github/workflows/docs.yml` does both and deploys to GitHub Pages from `main`.
- `faust2lv2` and `faust2jaqt` build in the current directory, so each effect is staged in `build/<name>/`, with `src/lib/*.lib` copied next to the `.dsp`. The bundle ends up in `build/<name>.lv2`.
- Plugin URI: `urn:pedalkit/<name>`.
- After `faust2lv2`, the Makefile runs `tools/fix-ttl.py` on the bundle's TTL. `faust2lv2` writes the licence as a string, and has no way to express `lv2:minorVersion`/`microVersion` or a plugin class. Without the script, `lv2lint` fails.
- If `src/<name>.presets.toml` exists, the Makefile then runs `tools/make-presets.py`. It maps labels to port symbols by reading the generated TTL (faust2lv2 names ports `<Label>_<index>`, e.g. `Bass_Shift_8`, so never hard-code symbols), fails on an unknown, missing or out-of-range control, writes `presets.ttl` and adds the presets to `manifest.ttl`. Check them with `jalv`: its `presets` command lists them, and `preset <URI>` followed by `controls` shows the applied values. Preset URIs are `urn:pedalkit/<name>/preset/<slug>`.
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
- **CLAP.** Faust 2.88 ships `faust2clap`, but the repo doesn't use it. It hard-codes the plugin ID as `org.faust.<name>` and the URL as faust.grame.fr, implements no latency extension (so the oversampler's delay never reaches the host), and needs CLAP and clap-helpers headers that Arch's `faust` package doesn't install. Instead, `tools/clap/faust-clap.cpp` is the repo's own architecture, written against the plain CLAP C API (MIT, header-only).
  - It mirrors the VST3 architecture. There is no GUI, and each Faust control becomes a parameter, numbered in UI order. A bargraph tagged `[lv2:reportsLatency]` becomes the latency extension. Extensions are audio-ports, params, state and latency. Parameter events are applied at their sample offset, and subnormals are flushed to zero during `process()`.
  - `make clap` compiles the `.dsp` into that architecture. `tools/clap-meta.py` writes `plugin_meta.h` (ID, name, description, vendor, version, homepage, features from `lv2class`) from the `declare`s, and the compiler links `build/<name>.clap` directly, with no CMake. The headers are cloned at a pinned tag (`CLAP_TAG` in the Makefile) into `build/clap`.
  - `make clap-validate` runs clap-validator on each plugin. `make install-clap` copies them to `~/.clap`.
- **CLAP plugin ID** is `pedalkit.<name>`, which matches the LV2 URI and the VST3 class ID. Like the VST3 class ID it must never change for a released effect. Parameter IDs and saved state follow the control order, as for VST3.
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
