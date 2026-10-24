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
| `codespell (typos)` | Common misspellings everywhere |
| `codespell (British English)` | American spellings in `.md`, `.dsp` and `.lib` files (word list in `tools/en-gb.codespell`) |
| `faust-compile` | Every `src/*.dsp` compiles (needs `faust` installed) |
| `reuse` | Every file has a machine-readable licence (an SPDX header or an entry in `REUSE.toml`) |
| `no-generated-files` | Nothing from `build/` or `tests/out/` is committed |
| Whitespace, YAML/TOML, shebangs, large files | General hygiene |

## GitHub Actions

### CI (`.github/workflows/ci.yml`)

Runs on every push to `main` and every pull request:

1. **Lint and format.** The pre-commit hooks above, except `faust-compile`, which the build job covers.
2. **Build, lv2lint and tests.** In an Arch Linux container, `make lv2 lint test describe` for every effect. The plots, CSV data and WAV renders from `tests/out/` are uploaded as the `test-output` artifact, and each effect's JSON description and block diagram as the `describe` artifact.
3. **VST3 build and pluginval.** In the same container, `make vst3` fetches the pinned VST3 SDK (cached between runs), builds each bundle and runs Steinberg's validator on it. `make pluginval` then runs pluginval at strictness 10. The bundles are uploaded as the `vst3` artifact.
4. **CLAP build and clap-validator.** In the same container, `make clap` fetches the pinned CLAP headers and builds each plugin. clap-validator is downloaded from its GitHub release, and `make clap-validate` runs it on every plugin. The plugins are uploaded as the `clap` artifact.

### Docs (`.github/workflows/docs.yml`)

Builds this site and publishes it to GitHub Pages:

1. In an Arch Linux container, build the test renderers and run `make test`, so the effect pages show the current measurements.
2. Build the site with `mkdocs build --strict` into `build/site/`. Any broken link, missing page or missing measurement fails the build.
3. On `main` only, deploy `build/site/` to GitHub Pages. Pull requests build the site but don't deploy it.

## Building this site locally

The site is built with [MkDocs](https://www.mkdocs.org/) and the [Material theme](https://squidfunk.github.io/mkdocs-material/). Install them into a virtual environment:

```sh
python -m venv .venv
.venv/bin/pip install -r tools/docs-requirements.txt
```

Then:

```sh
make test docs MKDOCS=.venv/bin/mkdocs         # build into build/site/
make docs-serve MKDOCS=.venv/bin/mkdocs        # live preview at http://127.0.0.1:8000/
```

Leave out `MKDOCS=…` if `mkdocs` is already on your `PATH`.

The pages are the Markdown files under `docs/`, and `mkdocs.yml` sets the navigation. `tools/mkdocs_hooks.py` adds the SVG and CSV files from `tests/out/<name>/` to the site as `measurements/<name>/`, which is why the tests must run first. The measurements are never committed.
