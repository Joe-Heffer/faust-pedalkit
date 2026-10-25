# Releasing

Each effect is versioned and released on its own. A release is a GitHub release for one effect, tagged `<name>-vX.Y.Z` (for example `bassdrive-v0.1.0`), with one tarball, `<name>-X.Y.Z-linux-x86_64.tar.gz`, and a `SHA256SUMS` file. The tarball holds the effect as LV2, VST3 and CLAP, plus `install.sh`, `README.txt`, `LICENSE` and the effect’s changelog as `CHANGELOG.md`.

The release is semi-automatic. Merging a version bump to `main` tags it, the tag builds, checks and drafts the release, and a person reviews the draft and publishes it. Nothing is published without that step.

The longer explanation, including why the release image differs from the everyday one, is in [`docs/development/releasing.md`](docs/development/releasing.md).

## Checklist

1. Set `declare version` in `src/<name>.dsp` to `X.Y.Z`. Hosts show this, and it goes into the LV2, VST3 and CLAP metadata.
2. In `docs/<name>/changelog.md`, move the `## [Unreleased]` entries into a new `## [X.Y.Z]` section. Update the `[Unreleased]` and `[X.Y.Z]` link references at the foot of the file. The section body becomes the release notes.
3. Merge to `main`. CI must be green.
4. Optional dry run: in the Actions tab, run *Release* with *Run workflow*. It builds and checks a tarball for every effect, keeps them as a workflow artifact and publishes nothing. Pull requests that touch `Dockerfile.release`, `tools/release/**` or `release.yml` run the same dry run.
5. The *Tag release* workflow runs on that merge and pushes `<name>-vX.Y.Z` for every effect whose version has no tag yet and has a changelog section. It then starts the *Release* workflow on the tag. To tag by hand instead (or if the workflow was skipped), run *Tag release* from the Actions tab, or:

    ```sh
    git tag -a <name>-vX.Y.Z -m "<Name> X.Y.Z"
    git push origin <name>-vX.Y.Z
    ```

6. Watch the *Release* workflow. It stops early if the tag is wrong (see below).
7. Open the draft on the [releases page](https://github.com/Joe-Heffer/faust-pedalkit/releases). Check the title, the tarball name, `SHA256SUMS` and the notes, then publish.
8. Confirm the links in the README and `docs/install.md` resolve.

## Automatic tagging

`.github/workflows/tag-release.yml` runs on pushes to `main` that touch `src/*.dsp` or `docs/*/changelog.md`, and on manual dispatch. `tools/release/untagged.py` lists the due tags: an effect is due when `declare version` has no tag and `release-info.py` accepts it. A version bump without a changelog section is skipped with a warning, so it releases once the section is merged. The workflow pushes an annotated tag for each due effect and dispatches *Release* on it, because a tag pushed with the default token does not start other workflows. It only creates tags. Publishing stays manual.

## What the workflow does

`.github/workflows/release.yml` runs on tags matching `*-v*`, on manual dispatch and on pull requests that touch the release files. Only a tag push reaches the last job.

* **build**
  * On a tag, `tools/release/release-info.py` fails unless the tag is `<name>-vX.Y.Z`, `src/<name>.dsp` exists, its `declare version` equals `X.Y.Z`, and `docs/<name>/changelog.md` has a `## [X.Y.Z]` section.
  * Builds `Dockerfile.release` (Debian 12, Faust built from source) and runs `make lv2 vst3 clap dist` in it, for the tagged effect only. A dry run builds every effect. Steinberg’s validator runs on each VST3 bundle during the build.
  * Uploads the tarballs and `SHA256SUMS` as the `release` artifact.
* **validate**
  * Verifies the checksums and unpacks the tarballs.
  * `tools/release/check-portable.sh` runs in stock Ubuntu 22.04 and Debian 12 and fails on any missing library or missing glibc or libstdc++ symbol version.
  * In the Arch toolchain image, `tools/release/validate.sh` runs `install.sh` into temporary folders, then lv2lint, pluginval (strictness 10) and clap-validator on the installed plugins, then `install.sh --uninstall`, which must leave the folders empty.
* **publish** (tags only)
  * Creates a **draft** release with `gh release create --verify-tag`, titled from `declare name` and the version.
  * The notes are the changelog section followed by short install instructions.
  * It does not publish, so a failed or odd release can be fixed or deleted before anyone sees it.

## Rules that must hold

* The tag, `declare version` and the changelog section must agree, or the workflow stops.
* Never rename a released `.dsp`. The LV2 URI (`urn:pedalkit/<name>`), VST3 class ID and CLAP ID (`pedalkit.<name>`) are derived from the name, and hosts store them in projects.
* Add new controls at the end. VST3 and CLAP store parameters by position.
* Keep `FAUST_VERSION` in `Dockerfile.release` in step with the Faust that `ARCH_SNAPSHOT` installs in `Dockerfile`.
* The release plugins target x86_64 Linux with glibc 2.35 or newer. Raising that floor needs a change to `Dockerfile.release` and to the install guide.

## Fixing a bad release

* **Workflow failed before publish:** fix the cause on `main`, delete the tag locally and on the remote (`git push origin :refs/tags/<tag>`), and tag the new commit. Nothing was published.
* **Draft is wrong:** delete the draft and the tag, then repeat from step 5. A tag that has been pushed once should not be moved after a release is public.
* **Published release is wrong:** do not replace the files. Release the next patch version with a changelog entry that says what changed.

## Not covered by the workflow

* Loading each format in a real host (Carla, Ardour, REAPER). Do this on the draft’s tarball before publishing, and file anything found as a separate issue.
* Only x86_64 Linux is built. There are no Windows, macOS or aarch64 builds.
* Release artefacts are checksummed but not signed.
