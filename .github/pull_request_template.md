# Summary

<!-- What changed and why. Link the issue, e.g. "Closes #123". -->

## Checklist

See [CONTRIBUTING.md](../CONTRIBUTING.md) and the hard rules in [AGENTS.md](../AGENTS.md#hard-rules). Tick each item or say why it doesn't apply.

- [ ] Design notes (`docs/<name>/design-notes.md`, original or circuit-inspired effects) and/or circuit notes (`docs/<name>/circuit-notes.md`, modelled parts) cover every new or changed constant, mark it documented, reported, inferred or chosen, give the intent of chosen values, and link the sources
- [ ] Clean-room: anything borrowed comes from public sources; no decompiled or proprietary code, binaries or firmware used, even as a reference
- [ ] `make lv2 lint test FX=<name>` passes, the tests check the design notes' measurable targets (original effects), and I have read the plots in `tests/out/<name>/`
- [ ] `pre-commit run --all-files` passes
- [ ] README has a row in the effect table and a controls table (new effects)
- [ ] No trademarks: plugin names, `declare name`, UI labels, URIs and file names are neutral
- [ ] British English in docs, comments and UI text
- [ ] New files have an SPDX header or a `REUSE.toml` entry

## What to listen for

<!--
The tests can't hear. Name the controls or constants a human should check by
ear, and at what settings, e.g. "Gain above 70: does the fizz from postLPF
sound harsh?". Write "n/a" if nothing audible changed.
-->
