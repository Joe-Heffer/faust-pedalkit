# Schematics

A schematic makes the circuit notes easier to check: which part sits where, which RC pair sets which corner frequency, and which values are sourced and which are inferred or chosen. Schematics are optional. When an effect has one, it is a KiCad schematic redrawn from the public sources listed in the circuit notes, never a copy of someone else's drawing, because a third party's drawing has its own copyright.

The first one is BassDrive's [stage 3, pre-emphasis](../bassdrive/circuit-notes.md#3-pre-emphasis-stage-1-r31-and-c10).

## File layout

```text
docs/<name>/schematics/
├── <name>.kicad_pro          project file (committed)
├── <name>.kicad_sch          root sheet (committed)
└── 3-pre-emphasis.kicad_sch  one sub-sheet per stage (committed)
```

- The root sheet is `<name>.kicad_sch`, next to a `<name>.kicad_pro` of the same name. The Makefile looks for exactly that path, and an effect without it is skipped.
- The root sheet holds one hierarchical sheet per stage, numbered and named like the section of the circuit notes it draws, for example "3 Pre-emphasis". Its file is the same name in lower case with hyphens, `3-pre-emphasis.kicad_sch`. Stages connect through hierarchical pins on the root sheet.
- Commit the `.kicad_sch` and `.kicad_pro` files only. `.gitignore` keeps out KiCad's local settings (`*.kicad_prl`), backups (`*-backups/`), caches (`fp-info-cache`) and autosaves.

## Symbols

Use only the stock KiCad symbol libraries (`Device`, `power`, `Amplifier_Operational`, `Simulation_SPICE` and so on), so that no custom library needs licensing. KiCad copies each symbol it uses into the schematic file, so the drawing renders without the libraries installed.

The KiCad libraries are licensed under CC-BY-SA 4.0 with an exception: for designs that use the library material, and the files generated from them, the copyright holders waive the share-alike condition. A schematic that places stock symbols can therefore carry its own licence, which here is CC-BY-4.0 like the rest of `docs/`. See the [KiCad library licence](https://www.kicad.org/libraries/license/) for the exact wording.

The BassDrive sheet was written by a script rather than in the KiCad editor, so its embedded symbol copies were typed from the library rather than copied from it. KiCad's ERC reports any difference as a warning. The next time someone opens the sheet in KiCad, run *Tools → Update Symbols from Library* and commit the result.

## Confidence and sources

Every component carries two custom fields, shown on the sheet under its reference and value:

| Field | Value |
|---|---|
| `Confidence` | `documented`, `reported`, `inferred` or `chosen`, as defined at the top of the circuit notes |
| `Source` | the circuit notes' reference number, e.g. `[2]`, or `-` for a chosen value |

When one part rests on claims of different strength (a reported value in an inferred position, say), `Confidence` gives the weaker one.

Draw every `inferred` or `chosen` part inside a dashed rectangle that encloses its symbol and fields. Documented and reported parts have no outline, so the guesswork stands out on the rendered sheet. A text note on each sub-sheet says what was inferred or chosen and why, in one line per part or group, and points to the section of the circuit notes.

## Designators

Designators match the ones in the circuit notes (R31, C10, IC2_C …). Parts that the notes add, with no counterpart in the sources, put an `X` after the type prefix: `RX1`, `CX1`, `RVX1`, `UX1`. They are numbered from 1 within each sheet set and are always `chosen` or `inferred`.

## Title block

| Field | Content |
|---|---|
| Title | the effect's neutral name, plus the stage on a sub-sheet ("BassDrive: 3 Pre-emphasis") |
| Company | "Redrawn from public sources; see circuit notes" |
| Comment 1 | "Licence: CC-BY-4.0" |
| Comment 2 | the reference hardware, named for identification only |
| Comment 3 | a key to the dashed outline |

The reference product name may appear only to identify the hardware, as in the circuit notes ([ground rule 2](index.md#ground-rules)). The plugin and file names stay neutral.

## Licensing

`REUSE.toml` already licenses everything under `docs/` as CC-BY-4.0, so the KiCad files need no SPDX header. `reuse lint` (the `reuse` pre-commit hook) checks them like any other file.

## Building

KiCad is large, so it lives in its own image, `Dockerfile.docs`, together with Faust and MkDocs. The docs workflow builds the site in it.

```sh
make erc                    # KiCad's electrical rules check on each schematic
make schematics             # one SVG per sheet into build/schematics/<name>/
make test schematics docs   # the whole site, schematics included

# the same in the docs image
make container DOCKERFILE=Dockerfile.docs IMAGE=pedalkit-docs RUN="test erc schematics docs"
```

Both targets take `FX=<name>`. Effects without a schematic are skipped, and the targets fail with an install hint if `kicad-cli` is missing (Arch: `pacman -S kicad kicad-library`).

- `make schematics` runs `kicad-cli sch export svg` on the root sheet. The file names are lower-cased with spaces turned into hyphens, giving `<name>.svg` for the root sheet and `<name>-<sheet>.svg` for each sub-sheet.
- `make erc` fails on any ERC error, such as an unconnected pin, an undriven input or a power pin with no source. Warnings, such as a library missing from a fresh KiCad configuration, go to `build/schematics/<name>/erc-all.rpt`. Give every power net a `PWR_FLAG` so ERC knows it is driven.

`tools/mkdocs_hooks.py` publishes `build/schematics/<name>/*.svg` on the site as `schematics/<name>/`, so a page embeds a sheet with:

```markdown
![Stage 3: pre-emphasis](../schematics/bassdrive/bassdrive-3-pre-emphasis.svg)
```

The SVGs are generated, so they are never committed. A missing schematic is not a warning, because not every effect has one, but a page that embeds a sheet that wasn't rendered fails the strict build on its broken link.
