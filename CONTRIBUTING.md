# Contributing

Thanks for helping. Whether you are a human or a coding agent, read [`AGENTS.md`](AGENTS.md) before you change anything. It is the authoritative checklist. This page summarises it and says how to get a change merged.

## Hard rules

The full wording is in [AGENTS.md § Hard rules](AGENTS.md#hard-rules). In short:

1. **Clean-room only.** Work from public schematics, circuit analyses, measurements, reviews and manuals. Never decompile, disassemble or copy a proprietary plugin, binary or firmware, and don't use one as a reference to match against. A pull request that breaks this rule will be closed, however good the result sounds.
2. **No trademarks.** Plugin names, `declare name`, UI labels, URIs and file names must be neutral. A manufacturer's product name may appear in the docs *only* to identify the reference hardware.
3. **British English** in documentation, comments and UI text: colour, behaviour, modelling, analyse, centre.
4. **Say when you're unsure.** Every circuit value is documented, reported, inferred or chosen, and the circuit notes say which, with a link for anything sourced.
5. **Ask before anything destructive or system-wide**, such as `sudo` or package installs.
6. **Judge sound by measurement**, and list what a human should check by ear.
7. **Open formats and machine-readable licensing.** Every new file has an SPDX header or a `REUSE.toml` entry. Code is MIT, `docs/` is CC-BY-4.0, committed audio is FLAC, and schematics are KiCad `.kicad_sch` redrawn from the sources.

## Workflow

1. Open an issue first, using the forms for bugs, modelling feedback or a new effect. For a new effect, the research comes before any DSP: see [Adding a new effect](AGENTS.md#adding-a-new-effect-name).
2. Set up the tools (see the README's [Dependencies](README.md#dependencies)) and install the hooks once with `pre-commit install`.
3. Make the change on a branch. Before you push, run:

   ```sh
   make lv2 lint test FX=<name>
   pre-commit run --all-files
   ```

   Read the plots in `tests/out/<name>/`, not just the pass/fail lines.
4. Open a pull request. The template has the checklist, so fill in every item or say why it doesn't apply. CI runs the same build, lint and tests.

## Contributions without code

Measurements of real hardware, corrections to the circuit notes backed by sources, and listening reports are all welcome. Use the "Sound or modelling feedback" issue form. Please don't attach audio or schematics you don't have the rights to share.

## Security

To report a vulnerability, see [SECURITY.md](SECURITY.md). Don't use a public issue.

## Licence

By contributing, you agree that your code is released under the MIT licence and your documentation under CC-BY-4.0, as described in the README's [Licence](README.md#licence) section.
