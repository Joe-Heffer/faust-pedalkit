# Releasing

Each effect is versioned and released on its own. A release is a GitHub release for one effect, tagged `<name>-vX.Y.Z` (for example `bassdrive-v0.1.0`), with one tarball, `<name>-X.Y.Z-linux-x86_64.tar.gz`, and its `SHA256SUMS`. The tarball holds that effect as LV2, VST3 and CLAP, plus `install.sh` (see [Install a release](../install.md#install-a-release)) and the effect's changelog. `.github/workflows/release.yml` builds and checks it, and leaves the release as a draft for a person to publish.

## Versions

An effect's version is the `declare version` in `src/<name>.dsp`. Hosts show it, and it goes into the LV2, VST3 and CLAP metadata. Every new effect starts at `0.1.0`, and each effect follows [Semantic Versioning](https://semver.org/) independently of the others. What changed in each version goes in `docs/<name>/changelog.md`, in [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format, which the site publishes beside the effect's page.

## Cutting a release

1. Set `declare version` in `src/<name>.dsp` to the new version, `X.Y.Z`.
2. In `docs/<name>/changelog.md`, move the `## [Unreleased]` entries into a new `## [X.Y.Z]` section, and add its link at the foot of the file.
3. Merge that to `main`, then tag the merge commit and push the tag:

    ```sh
    git tag -a <name>-vX.Y.Z -m "<Name> X.Y.Z"
    git push origin <name>-vX.Y.Z
    ```

4. Watch the *Release* workflow. `tools/release/release-info.py` fails it straight away if the tag names no effect, doesn't match the effect's `declare version`, or has no section in its changelog.
5. Open the draft on the [releases page](https://github.com/Joe-Heffer/faust-pedalkit/releases). Its title is the effect's name and version, and its notes are the changelog section. Check them, then publish it.

To try the workflow without releasing, run it from the Actions tab (*Run workflow*). It builds and checks a tarball for every effect and uploads them as a workflow artifact, but publishes nothing. Pull requests that touch the release files run it the same way.

!!! warning "IDs never change"
    Hosts store the LV2 URI (`urn:pedalkit/<name>`), the VST3 class ID (derived from `pedalkit.<name>`) and the CLAP ID (`pedalkit.<name>`) in saved projects, and VST3 and CLAP store parameters by position. Once an effect has been released, don't rename its `.dsp`, and add new controls at the end. See [Adding an effect](adding-an-effect.md).

## What the workflow does

| Job | What it checks |
|---|---|
| **build** | On a tag, checks it with `tools/release/release-info.py`. Builds `Dockerfile.release` (Debian 12, Faust built from source) and runs `make lv2 vst3 clap dist` in it, for the tagged effect or, on a dry run, for every effect. Steinberg's validator runs on each VST3 bundle as part of the build. |
| **validate** | In stock Ubuntu 22.04, `tools/release/check-portable.sh` checks that every plugin binary links: no missing libraries and no missing glibc or libstdc++ symbol versions. It prints the newest versions each binary needs (currently `GLIBC_2.35` and `GLIBCXX_3.4.29`). In the Arch toolchain image, `lv2lint`, pluginval (strictness 10) and clap-validator run on the plugins *as shipped*, and `install.sh` installs into and uninstalls from temporary folders. |
| **publish** | On a tag only: creates the draft release with the tarball and `SHA256SUMS`, titled from the effect's `declare name`, with the changelog section as its notes. |

## Why a separate image

The everyday toolchain image (`Dockerfile`) is Arch, which ships a newer glibc than most distributions, so plugins built there may not load on Ubuntu or Debian. `Dockerfile.release` uses Debian 12, the oldest base whose own packages cover the build: Python 3.11 for `tomllib` (`tools/make-presets.py`) and CMake 3.25 (the VST3 SDK's minimum). It builds Faust from the release tarball at `FAUST_VERSION`, pinned by checksum. It sets `LDFLAGS="-static-libgcc"`, which the Makefile passes to every plugin link line. libstdc++ stays dynamic on purpose: Debian 12's static libstdc++ calls `arc4random`, which only exists from glibc 2.36, whereas Ubuntu 22.04 already ships the same GCC 12 libstdc++.

Keep `FAUST_VERSION` in step with the Faust that `ARCH_SNAPSHOT` installs in `Dockerfile`, so the released plugins come from the same compiler that CI tests.

To build a release locally:

```sh
make container DOCKERFILE=Dockerfile.release IMAGE=pedalkit-release RUN="lv2 vst3 clap dist" FX=bassdrive
ls build/dist/                     # bassdrive-<version>-linux-x86_64.tar.gz and SHA256SUMS
```

Without `FX`, `make dist` packs one tarball per effect. It also works on the host, but the result only runs on systems with a glibc at least as new as yours.
