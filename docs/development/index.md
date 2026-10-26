# Development

This section is for anyone, human or coding agent, adding an effect or changing an existing one. [`AGENTS.md`](https://github.com/Joe-Heffer/faust-pedalkit/blob/main/AGENTS.md) in the repository is the short checklist. These pages explain the same rules in more depth. To get a change merged, see [`CONTRIBUTING.md`](https://github.com/Joe-Heffer/faust-pedalkit/blob/main/CONTRIBUTING.md). To report a vulnerability, see [`SECURITY.md`](https://github.com/Joe-Heffer/faust-pedalkit/blob/main/SECURITY.md).

- [How it works](how-it-works.md): what DSP and Faust are, and how one `.dsp` file becomes LV2, VST3 and CLAP plugins plus measurements. Start here if you are new to either.
- [Designing new sounds](designing-new-sounds.md): the project's aim, the three kinds of effect, and how to write design notes for an original one.
- [Designing for feel](designing-for-feel.md): the mechanisms behind how an effect responds to the playing, how to build them in Faust and how to measure them.
- [Adding an effect](adding-an-effect.md): from notes to DSP, tests and docs.
- [Shared library](pedalkit-lib.md): the oversampler, clippers and safety limiter in `pedalkit.lib`.
- [Tests and measurements](testing.md): the render harness, the Python helpers and what every effect must check.
- [Schematics](schematics.md): how to draw an effect's reference circuit in KiCad, and how it reaches this site.
- [Linting and CI](ci.md): pre-commit hooks, GitHub Actions and how this site is published.
- [Releasing](releasing.md): cutting a release and how the release workflow builds portable plugins.
- [Agent skill](https://github.com/Joe-Heffer/faust-pedalkit/tree/main/.claude/skills/pedalkit-effect): a Claude Code skill (`pedalkit-effect`) that walks an agent through the whole effect workflow, from notes to PR.

## Ground rules

1. **Clean-room only.** Anything taken from existing hardware or software comes from public schematics, circuit analyses, measurements, reviews and manuals. Never decompile, disassemble or copy a proprietary plugin, binary or firmware, and don't use one as a reference to match against. Original designs invent rather than imitate.
2. **No trademarks.** Plugin names, `declare name`, UI labels, URIs and file names must be neutral. A manufacturer's product name may appear in the docs *only* to identify reference or inspiring hardware, never as branding. The `no-trademarks` pre-commit hook enforces this against the deny-list in `tools/trademarks.txt` (see [Linting and CI](ci.md#extending-the-trademark-deny-list)).
3. **British English** in all documentation, comments and UI text: colour, behaviour, modelling, analyse, centre.
4. **Say when you're unsure, and why a value is what it is.** Every constant in the DSP is documented, reported, inferred or chosen. The design or circuit notes say which, with a link for anything sourced and the intent behind anything chosen.
5. **Judge sound by measurement.** Describe results in terms of harmonics, frequency response, aliasing and levels, and list the parameters a human should tune by ear.
6. **Open formats and machine-readable licensing.** Every file carries an SPDX header or has an entry in `REUSE.toml`. Committed audio is FLAC. Schematics are KiCad `.kicad_sch`, redrawn from the sources.

## Build mechanics

- `faust2lv2` and `faust2jaqt` build in the current directory, so each effect is staged in `build/<name>/` with `src/lib/*.lib` copied next to the `.dsp`. The bundle ends up in `build/<name>.lv2`.
- After `faust2lv2`, the Makefile runs `tools/fix-ttl.py` on the bundle's TTL. `faust2lv2` writes the licence as a string and cannot express `lv2:minorVersion`, `lv2:microVersion` or a plugin class, so `lv2lint` fails without the fix-up.
- `faust2lv2` needs the Boost headers, even for effects without MIDI.
- **VST3.** No Faust script builds VST3, and `faust2juce` goes through JUCE (AGPL or commercial), so `tools/vst3/faust-vst3.cpp` is this repository's own architecture, written against the MIT VST3 SDK. It is a single-component effect with no GUI. Each Faust control becomes a parameter in UI order, and a bargraph tagged `[lv2:reportsLatency]` becomes the latency report. `tools/vst3-meta.py` writes the name, vendor, version, category and class ID from the `declare` lines, and `tools/vst3/CMakeLists.txt` builds `build/<name>.vst3`. The SDK is cloned at a pinned tag (`VST3_SDK_TAG` in the Makefile) into `build/vst3sdk`.
- **CLAP.** `faust2clap` hard-codes the plugin ID, implements no latency extension and needs headers that Arch's `faust` package does not install, so `tools/clap/faust-clap.cpp` is the repository's own architecture, written against the plain CLAP C API. It mirrors the VST3 one: no GUI, parameters in UI order, latency from the tagged bargraph, parameter events applied at their sample offset. `tools/clap-meta.py` writes the metadata, and the compiler links `build/<name>.clap` directly. The headers are cloned at a pinned tag (`CLAP_TAG`) into `build/clap`.
- **Identity.** The VST3 class ID is `uuid5(NAMESPACE_DNS, "pedalkit.<name>")` and the CLAP ID is `pedalkit.<name>`, matching the LV2 URI `urn:pedalkit/<name>`. None of them may change for a released effect. Parameter IDs and saved state follow the order of the controls (the `[n]` prefixes), so append new controls at the end.
- `make describe` writes a format-neutral description of each effect. `faust -json` gives `build/<name>/<name>.dsp.json` (every control's label, unit, range and default), and `faust -svg` gives the block diagram in `build/<name>/<name>-svg/`.
- Generated files only ever go in `build/` and `tests/out/`, and are never committed.
