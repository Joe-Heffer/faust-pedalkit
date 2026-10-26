# Contributing

Thanks for helping. This project is about making effects that don't exist yet; modelling classic hardware is a way to learn and to collect building blocks, not the end in itself. [Designing new sounds](docs/development/designing-new-sounds.md) explains the approach.

Whether you are a human or a coding agent, read [`AGENTS.md`](AGENTS.md) before you change anything. It is the authoritative checklist. This page summarises it and says how to get a change merged. Claude Code users also get a project skill, [`pedalkit-effect`](.claude/skills/pedalkit-effect/SKILL.md), that walks through adding an effect step by step.

## Hard rules

The full wording is in [AGENTS.md § Hard rules](AGENTS.md#hard-rules). In short:

1. **Clean-room only.** Anything taken from existing hardware or software comes from public schematics, circuit analyses, measurements, reviews and manuals. Never decompile, disassemble or copy a proprietary plugin, binary or firmware, and don't use one as a reference to match against. Original designs invent rather than imitate. A pull request that breaks this rule will be closed, however good the result sounds.
2. **No trademarks.** Plugin names, `declare name`, UI labels, URIs and file names must be neutral. A manufacturer's product name may appear in the docs *only* to identify reference or inspiring hardware.
3. **British English** in documentation, comments and UI text: colour, behaviour, modelling, analyse, centre.
4. **Say when you're unsure, and why a value is what it is.** Every constant is documented, reported, inferred or chosen, and the design or circuit notes say which, with a link for anything sourced and the intent behind anything chosen.
5. **Ask before anything destructive or system-wide**, such as `sudo` or package installs.
6. **Judge sound by measurement**, and list what a human should check by ear.
7. **Open formats and machine-readable licensing.** Every new file has an SPDX header or a `REUSE.toml` entry. Code is MIT, `docs/` is CC-BY-4.0, committed audio is FLAC, and schematics are KiCad `.kicad_sch` redrawn from the sources.

## Workflow

1. Open an issue first, using the forms for bugs, sound feedback or a new effect. A new effect can be an original idea; sources are needed only for what it borrows from existing hardware. The design or circuit notes come before any DSP: see [Adding a new effect](AGENTS.md#adding-a-new-effect-name).
2. Set up the tools (see the README's [Dependencies](README.md#dependencies)) and install the hooks once with `pre-commit install`.
3. Make the change on a branch. Before you push, run:

   ```sh
   make lv2 lint test FX=<name>
   pre-commit run --all-files
   ```

   Read the plots in `tests/out/<name>/`, not just the pass/fail lines. `make test` also runs the checks in `tests/common/` on every effect: latency, zipper noise, CPU use and recovery. [Playing feel, CPU and stability](docs/development/feel-cpu-stability.md) explains them.
4. Open a pull request. The template has the checklist, so fill in every item or say why it doesn't apply. CI runs the same build, lint and tests.

## Contributions without code

Effect ideas, listening reports, measurements of real hardware and corrections to the notes backed by sources are all welcome. Use the "New effect idea" or "Sound feedback" issue forms. Please don't attach audio or schematics you don't have the rights to share.

## Security

To report a vulnerability, see [SECURITY.md](SECURITY.md). Don't use a public issue.

## Licence

By contributing, you agree that your code is released under the MIT licence and your documentation under CC-BY-4.0, as described in the README's [Licence](README.md#licence) section.
