# Development

This section is for anyone, human or coding agent, adding an effect or changing an existing one. [`AGENTS.md`](https://github.com/Joe-Heffer/faust-pedalkit/blob/main/AGENTS.md) in the repository is the short checklist. These pages explain the same rules in more depth. To get a change merged, see [`CONTRIBUTING.md`](https://github.com/Joe-Heffer/faust-pedalkit/blob/main/CONTRIBUTING.md). To report a vulnerability, see [`SECURITY.md`](https://github.com/Joe-Heffer/faust-pedalkit/blob/main/SECURITY.md).

- [Designing new sounds](designing-new-sounds.md): the project's aim, the three kinds of effect, and how to write design notes for an original one.
- [Adding an effect](adding-an-effect.md): from notes to DSP, tests and docs.
- [Shared library](pedalkit-lib.md): the oversampler, clippers and safety limiter in `pedalkit.lib`.
- [Tests and measurements](testing.md): the render harness, the Python helpers and what every effect must check.
- [Linting and CI](ci.md): pre-commit hooks, GitHub Actions and how this site is published.
- [Releasing](releasing.md): cutting a release and how the release workflow builds portable plugins.

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
- `make describe` writes a format-neutral description of each effect. `faust -json` gives `build/<name>/<name>.dsp.json` (every control's label, unit, range and default), and `faust -svg` gives the block diagram in `build/<name>/<name>-svg/`.
- Generated files only ever go in `build/` and `tests/out/`, and are never committed.
