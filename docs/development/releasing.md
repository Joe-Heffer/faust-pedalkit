# Releasing

A release is a GitHub release with one tarball, `pedalkit-<version>-linux-x86_64.tar.gz`, and its `SHA256SUMS`. The tarball holds every effect as LV2, VST3 and CLAP, plus `install.sh` (see [Install a release](../install.md#install-a-release)). `.github/workflows/release.yml` builds and checks it, and leaves the release as a draft for a person to publish.

## Cutting a release

1. Set `version` in `CITATION.cff` to the new project version, `X.Y.Z`. The release tag, the tarball name and the citation all come from it.
2. Bump `declare version` in each `src/<name>.dsp` that changed since the last release. Effects keep their own versions, which hosts show; they need not match the project's.
3. Add a section for the version to `CHANGELOG.md`.
4. Merge that to `main`, then tag the merge commit and push the tag:

    ```sh
    git tag -a vX.Y.Z -m "pedalkit X.Y.Z"
    git push origin vX.Y.Z
    ```

5. Watch the *Release* workflow. It fails straight away if the tag doesn't match `CITATION.cff`.
6. Open the draft on the [releases page](https://github.com/Joe-Heffer/faust-pedalkit/releases), edit the generated notes (lead with the `CHANGELOG.md` section), and publish it.

To try the workflow without releasing, run it from the Actions tab (*Run workflow*). It builds and checks the tarball and uploads it as a workflow artifact, but publishes nothing. Pull requests that touch the release files run it the same way.

!!! warning "IDs never change"
    Hosts store the LV2 URI (`urn:pedalkit/<name>`), the VST3 class ID (derived from `pedalkit.<name>`) and the CLAP ID (`pedalkit.<name>`) in saved projects, and VST3 and CLAP store parameters by position. Once an effect has been released, don't rename its `.dsp`, and add new controls at the end. See [Adding an effect](adding-an-effect.md).

## What the workflow does

| Job | What it checks |
|---|---|
| **build** | Builds `Dockerfile.release` (Debian 12, Faust built from source) and runs `make lv2 vst3 clap dist` in it. Steinberg's validator runs on each VST3 bundle as part of the build. |
| **validate** | In stock Ubuntu 22.04, `tools/release/check-portable.sh` checks that every plugin binary links: no missing libraries or glibc symbol versions, and no libstdc++ dependency. In the Arch toolchain image, `lv2lint`, pluginval (strictness 10) and clap-validator run on the plugins *as shipped*, and `install.sh` installs into and uninstalls from temporary folders. |
| **publish** | On a tag only: creates the draft release with the tarball and `SHA256SUMS`. |

## Why a separate image

The everyday toolchain image (`Dockerfile`) is Arch, which ships a newer glibc than most distributions, so plugins built there may not load on Ubuntu or Debian. `Dockerfile.release` uses Debian 12, the oldest base whose own packages cover the build: Python 3.11 for `tomllib` (`tools/make-presets.py`) and CMake 3.25 (the VST3 SDK's minimum). It builds Faust from the release tarball at `FAUST_VERSION`, pinned by checksum. It sets `LDFLAGS="-static-libstdc++ -static-libgcc"`, which the Makefile passes to every plugin link line.

Keep `FAUST_VERSION` in step with the Faust that `ARCH_SNAPSHOT` installs in `Dockerfile`, so the released plugins come from the same compiler that CI tests.

To build a release locally:

```sh
make container DOCKERFILE=Dockerfile.release IMAGE=pedalkit-release RUN="lv2 vst3 clap dist"
ls build/dist/                     # the tarball and SHA256SUMS
```

`make dist` also works on the host, but the result only runs on systems with a glibc at least as new as yours.
