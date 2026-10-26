# Linting and CI

## Pre-commit hooks

[pre-commit](https://pre-commit.com/) runs the linters and formatters before each commit:

```sh
pipx install pre-commit   # or: pacman -S python-pre-commit
pre-commit install        # once per clone
pre-commit run --all-files
```

| Hook | Checks |
|---|---|
| `ruff-check`, `ruff-format` | Python lint and formatting (configured in `pyproject.toml`) |
| `shellcheck` | Shell scripts |
| `markdownlint-cli2` | Markdown, including this site (configured in `.markdownlint-cli2.yaml`) |
| `actionlint` | GitHub Actions workflows: syntax, `${{ }}` expressions, job dependencies and action inputs |
| `workflow-permissions` | Each workflow sets a top-level `permissions:` with no write scope, nothing uses `write-all`, and every `uses:` names a version tag or commit SHA rather than a branch (`tools/check-workflows.py`) |
| `codespell (typos)` | Common misspellings everywhere |
| `codespell (British English)` | American spellings in `.md`, `.dsp` and `.lib` files (word list in `tools/en-gb.codespell`) |
| `faust-compile` | Every `src/*.dsp` compiles (needs `faust` installed) |
| `reuse` | Every file has a machine-readable licence (an SPDX header or an entry in `REUSE.toml`) |
| `no-generated-files` | Nothing from `build/` or `tests/out/` is committed |
| `no-trademarks` | No manufacturer or product name from `tools/trademarks.txt` in any file name, or in `src/` and `tests/` (`declare` lines, UI labels, URIs). `docs/` is not scanned |
| Whitespace, YAML/TOML, shebangs, large files | General hygiene |

### Extending the trademark deny-list

`tools/trademarks.txt` holds one name per line; lines starting with `#` are comments. When you model a new piece of hardware, add its manufacturer and product names there in the same commit as the circuit notes. Matching ignores case, spaces, hyphens, underscores and CamelCase, and only matches whole words, so `Sans Amp` also catches `SansAmp`, `sans_amp` and `SANSAMP`, and `Boss` catches `BossDrive` but not `emboss`. Leave out names that are ordinary words (such as `Orange` or `Rat`), which would flag normal prose; list the full product name instead. Check the result with `pre-commit run no-trademarks --all-files`.

## GitHub Actions

Every workflow starts from a read-only token (`permissions: contents: read`, or `{}`), and a job that needs to write declares just those scopes itself. At present that is only Dependabot auto-merge (`contents` and `pull-requests`) and the Pages deployment (`pages` and `id-token`). Checkouts set `persist-credentials: false`, because no job pushes. Actions are referenced by version tag and kept current by Dependabot.

### CI (`.github/workflows/ci.yml`)

Runs on every push to `main` and every pull request:

1. **Lint and format.** The pre-commit hooks above, except `faust-compile`, which the build job covers.
2. **Build, lv2lint and tests.** In an Arch Linux container, `make lv2 lint test describe` for every effect. The plots, CSV data and WAV renders from `tests/out/` are uploaded as the `test-output` artifact, and each effect's JSON description and block diagram as the `describe` artifact.
3. **VST3 build and pluginval.** In the same container, `make vst3` fetches the pinned VST3 SDK (cached between runs), builds each bundle and runs Steinberg's validator on it. `make pluginval` then runs pluginval at strictness 10. The bundles are uploaded as the `vst3` artifact.
4. **CLAP build and clap-validator.** In the same container, `make clap` fetches the pinned CLAP headers and builds each plugin. clap-validator is downloaded from its GitHub release, and `make clap-validate` runs it on every plugin. Its `preset-discovery-crawl` and `preset-discovery-load` tests are skipped, because clap-validator deadlocks on any container of two or more presets; `tools/clap/check-presets.cpp` crawls and loads the presets instead and checks every parameter against the effect's `presets.h`. The plugins are uploaded as the `clap` artifact.

### Docs (`.github/workflows/docs.yml`)

Builds this site and publishes it to GitHub Pages:

1. Build the docs image (`Dockerfile.docs`: the Faust toolchain plus KiCad and MkDocs) and, in it, run `make test`, so the effect pages show the current measurements.
2. Run `make erc` and `make schematics`, which check each effect's KiCad schematic and render it to SVG (see [Schematics](schematics.md)).
3. Build the site with `mkdocs build --strict` into `build/site/`. Any broken link, missing page or missing measurement fails the build.
4. On `main` only, deploy `build/site/` to GitHub Pages. Pull requests build the site but don't deploy it.

## Building this site locally

The site is built with [MkDocs](https://www.mkdocs.org/) and the [Material theme](https://squidfunk.github.io/mkdocs-material/). Install them into a virtual environment:

```sh
python -m venv .venv
.venv/bin/pip install -r tools/docs-requirements.txt
```

Then:

```sh
make test schematics docs MKDOCS=.venv/bin/mkdocs  # build into build/site/
make docs-serve MKDOCS=.venv/bin/mkdocs             # live preview at http://127.0.0.1:8000/
```

Leave out `MKDOCS=…` if `mkdocs` is already on your `PATH`. `make schematics` needs KiCad's `kicad-cli`.

The pages are the Markdown files under `docs/`, and `mkdocs.yml` sets the navigation. `tools/mkdocs_hooks.py` adds the SVG and CSV files from `tests/out/<name>/` to the site as `measurements/<name>/`, which is why the tests must run first. It adds the schematic sheets from `build/schematics/<name>/` as `schematics/<name>/` in the same way. Without `make schematics`, a page that embeds a sheet fails the strict build on its broken link. The measurements and sheets are never committed.

Or build everything in the docs image, which has KiCad and MkDocs installed:

```sh
make container DOCKERFILE=Dockerfile.docs IMAGE=pedalkit-docs RUN="test erc schematics docs"
```
