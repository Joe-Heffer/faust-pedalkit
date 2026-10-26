# Faust Pedal Kit

[![CI](https://github.com/Joe-Heffer/faust-pedalkit/actions/workflows/ci.yml/badge.svg)](https://github.com/Joe-Heffer/faust-pedalkit/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/Joe-Heffer/faust-pedalkit?include_prereleases&sort=semver)](https://github.com/Joe-Heffer/faust-pedalkit/releases)

A workshop for designing new guitar and bass effects in Faust: new sounds, and new kinds of effect, built as native Linux LV2, VST3 and CLAP plugins and checked by offline measurement tests.

**Documentation: <https://joe-heffer.github.io/faust-pedalkit/>**, with each effect's controls, design and circuit research, and current measurement plots.

[Faust](https://faust.grame.fr/) makes it cheap to try ideas a box of components can't easily be: clippers whose shape follows the playing, filters that track pitch, stages that never share a circuit board. Each effect is compiled to an LV2, a VST3 and a CLAP plugin, with an optional standalone JACK build, and has offline tests that render signals and check them numerically, so a new idea is measured before anyone has to trust their ears.

Studying classic hardware is part of the method rather than the goal. Clean-room models of well-known pedals show how they get their character, calibrate the measurement tools against something known, and supply tested building blocks (clippers, analogue filter sections, voicings) for original designs to reuse, bend and recombine. Each effect is one of:

- **Original:** a sonic idea with no single reference device, written up in design notes.
- **Circuit-inspired:** a real circuit deliberately taken somewhere it couldn't go.
- **Modelled:** a measured, sourced model of one device, written up in circuit notes.

The two effects so far are models. Original and circuit-inspired effects are where the project is heading: see [Designing new sounds](docs/development/designing-new-sounds.md).

| Effect | Kind | Description | Notes |
|---|---|---|---|
| **BassDrive** (`src/bassdrive.dsp`) | Modelled | Bass overdrive with clean/driven blend and two-band EQ, modelled on a classic compact bass overdrive pedal | [circuit notes](docs/bassdrive/circuit-notes.md) |
| **BassPreamp** (`src/basspreamp.dsp`) | Modelled | Tube-voiced bass preamp/DI with blend, presence, built-in speaker voicing and three-band EQ with shiftable bass and mid, modelled on a classic bass preamp/DI pedal | [circuit notes](docs/basspreamp/circuit-notes.md) |

To hear them without installing anything, open the [browser demo](https://joe-heffer.github.io/faust-pedalkit/demo/): the same Faust code compiled to WebAssembly, with a test riff, an audio file or live input ([how it works](docs/usage/browser.md)).

New to DSP or Faust? [How it works](docs/development/how-it-works.md) explains what an effect is in code, how Faust describes it, and how one `.dsp` file becomes LV2, VST3 and CLAP plugins plus measurements. [Adding an effect](docs/development/adding-an-effect.md) is the step-by-step workflow.

## Install

Each effect is released on its own. Download its tarball from the [releases page](https://github.com/Joe-Heffer/faust-pedalkit/releases) (tagged `<name>-v<version>`), unpack it and run its installer:

```sh
tar -xzf bassdrive-*-linux-x86_64.tar.gz
cd bassdrive-*-linux-x86_64
./install.sh          # copies the LV2, VST3 and CLAP plugins into ~/.lv2, ~/.vst3 and ~/.clap
```

Then rescan plugins in your DAW. `./install.sh --help` lists the options, including `--uninstall`. The release plugins need x86_64 Linux with glibc 2.35 or newer (Ubuntu 22.04, Debian 12 or later). See [Install and build](https://joe-heffer.github.io/faust-pedalkit/install/) for details, or read on to build from source.

## Layout

```text
src/<name>.dsp              one file per effect
src/<name>.presets.toml     optional factory presets, built into the LV2, VST3 and CLAP plugins
src/lib/pedalkit.lib        shared blocks: 4x oversampler, clippers, analogue filter sections, output safety limiter
docs/<name>/design-notes.md   an original effect's idea, inspirations, design choices and targets
docs/<name>/circuit-notes.md  a modelled circuit's research, sources and modelling decisions
tests/lib/                  render harness (Faust architecture) and Python helpers
tests/<name>/test_*.py      offline tests for one effect
tools/fix-ttl.py            adds LV2 metadata that faust2lv2 cannot write (licence URI, version, class)
tools/presets.py            turns src/<name>.presets.toml into LV2 presets and a header for VST3 and CLAP
tools/basspreamp-networks.py  derives BassPreamp's fixed filter networks from component values (numpy)
tools/vst3/                 VST3 architecture (Faust) and CMake project for the VST3 SDK
tools/vst3-meta.py          writes each VST3 plugin's name, version, category and class ID
tools/clap/faust-clap.cpp   CLAP architecture (Faust), written against the CLAP headers
tools/clap-meta.py          writes each CLAP plugin's ID, name, version and features
tests/run.sh <name>         runs one effect's tests
build/                      generated (bundles, renderers)
tests/out/<name>/           generated plots (SVG), data (CSV) and WAV renders
```

## Dependencies

| Purpose | Arch | Debian / Ubuntu |
|---|---|---|
| Faust compiler and `faust2lv2` | `faust` | `faust` |
| Boost headers (needed by Faust's LV2 template) | `boost` | `libboost-dev` |
| C++ compiler | `gcc` (or `clang`) | `g++` |
| LV2 headers | `lv2` | `lv2-dev` |
| Standalone JACK build (`faust2jaqt`) | `qt5-base`, `jack2` or `pipewire-jack` | `qtbase5-dev`, `libjack-jackd2-dev` |
| VST3 build (fetches the VST3 SDK into `build/`) | `cmake`, `git` | `cmake`, `git` |
| CLAP build (fetches the CLAP headers into `build/`) | `git` | `git` |
| Validation | `lv2lint`; [pluginval](https://github.com/Tracktion/pluginval/releases) for VST3; [clap-validator](https://github.com/free-audio/clap-validator/releases) for CLAP | `lv2lint`; pluginval; clap-validator |
| Quick host for testing | `jalv` | `jalv` |
| Tests and presets (Python 3.11 or newer) | `python-numpy`, `python-matplotlib` | `python3-numpy`, `python3-matplotlib` |
| Optional audio tools | `sox` | `sox` |

Development used Faust 2.88. Older distribution packages may be missing library functions used here, such as `fi.dcblockerat` or `fi.peak_eq_cq`. If the build fails with an "undefined symbol" error from Faust, install a newer Faust (see <https://github.com/grame-cncm/faust/releases>).

### Arch

```sh
sudo pacman -S --needed faust boost gcc lv2 lv2lint jalv sox python-numpy python-matplotlib qt5-base \
                        cmake git
```

Faust is linked against the system LLVM. If `faust` fails with `libLLVM.so.NN: cannot open shared object file`, the system is partially upgraded. Run `sudo pacman -Syu` to fix it.

### Debian / Ubuntu

```sh
sudo apt install faust libboost-dev g++ lv2-dev lv2lint jalv sox cmake git \
                 python3-numpy python3-matplotlib qtbase5-dev libjack-jackd2-dev
```

### In a container (any OS)

If your distribution's Faust is too old, or you are on macOS or Windows (WSL), build and test inside the toolchain image instead. The `Dockerfile` pins Faust and the other tools to a dated Arch Linux snapshot, and CI uses the same image. Only Docker or Podman is needed on the host.

```sh
make container                            # builds the image, then runs make lv2 lint test inside it
make container RUN="describe" FX=bassdrive
make container RUN="vst3 pluginval"
make container CONTAINER=podman           # Podman instead of Docker
```

The repository is mounted into the container, so the results land in `build/` and `tests/out/` as usual, owned by you. `CONTAINER_FLAGS` passes extra options to `docker run`, for example `CONTAINER_FLAGS="--dns 1.1.1.1"` if containers on your machine cannot resolve host names. Run `make install` and the listening hosts (`jalv`, a DAW) on the host, not in the container.

The bundles are built against Arch's current glibc, so they may not load on older distributions, such as an Ubuntu LTS release. They are Linux binaries, so they don't run in macOS or Windows hosts either. Use the container to build and test, and build natively for the machine you play on.

## Build, test and install

```sh
git clone https://github.com/Joe-Heffer/faust-pedalkit.git
cd faust-pedalkit
```

`faust2lv2` prints "bad port property 'unit:…'" and "'tooltip:…'" messages during the build. These come from a quirk in Faust's LV2 template and are harmless: the units and tooltips are written to the plugin description correctly.

```sh
make lv2                  # build/<name>.lv2 for every effect
make lint                 # lv2lint on every bundle (passes; only an author e-mail warning)
make test                 # renders, checks, and writes SVG plots and CSV data to tests/out/
make describe             # build/<name>/<name>.dsp.json (controls) and block-diagram SVGs
make schematics           # KiCad schematics to SVG in build/schematics/<name>/ (needs kicad-cli)
make erc                  # KiCad's electrical rules check on each schematic
make web                  # browser demo into build/web/ (needs Node.js and npm)
make web-test             # compare the browser build with the native renderer
make docs                 # documentation site into build/site/ (after make test web schematics; see below)
make standalone           # build/<name>/<name> (JACK, Qt GUI)
make install              # copies bundles to ~/.lv2
make vst3                 # build/bassdrive.vst3 (fetches the VST3 SDK on first use)
make pluginval            # pluginval at strictness 10 on every VST3 bundle
make install-vst3         # copies VST3 bundles to ~/.vst3
make clap                 # build/bassdrive.clap (fetches the CLAP headers on first use)
make clap-validate        # clap-validator on every CLAP plugin
make install-clap         # copies CLAP plugins to ~/.clap
make uninstall            # removes all three
make check                # every pre-commit hook on every file, as CI runs them
make format               # fix Python lint and formatting with ruff
make clean                # removes build/ and tests/out/ (keeps the VST3 SDK; make distclean removes it)
make help                 # lists every target and effect
```

Add `FX=bassdrive` or `FX=basspreamp` to any target to build one effect only.

Plugin URIs have the form `urn:pedalkit/<name>`, so BassDrive is `urn:pedalkit/bassdrive` and BassPreamp is `urn:pedalkit/basspreamp`. The matching CLAP plugin ID is `pedalkit.<name>`, here `pedalkit.bassdrive`.

The VST3 build uses Steinberg's [VST3 SDK](https://github.com/steinbergmedia/vst3sdk), which has been MIT-licensed since version 3.8. `make vst3` clones a pinned release into `build/vst3sdk` (only the submodules it needs), or uses an existing checkout given as `VST3_SDK=/path/to/vst3sdk`. The SDK's validator runs on each bundle as part of the build. For `make pluginval`, download pluginval and put it on `PATH`, or pass `PLUGINVAL=/path/to/pluginval`. The VST3 plugins have no custom GUI, so hosts show their generic parameter editor.

The CLAP build needs only the MIT-licensed [CLAP headers](https://github.com/free-audio/clap). `make clap` clones a pinned release into `build/clap`, or uses an existing checkout given as `CLAP_SDK=/path/to/clap`. For `make clap-validate`, download [clap-validator](https://github.com/free-audio/clap-validator/releases) and put it on `PATH`, or pass `CLAP_VALIDATOR=/path/to/clap-validator`. Like the VST3 plugins, the CLAP plugins have no custom GUI.

Quick check from a terminal once it is installed:

```sh
jalv urn:pedalkit/bassdrive          # console host; jalv.gtk3 or jalv.qt5 for a GUI if packaged
```

### Linting and CI

[pre-commit](https://pre-commit.com/) runs the linters and formatters before each commit:

```sh
pipx install pre-commit   # or: pacman -S python-pre-commit
pre-commit install        # once per clone
make check                # same as: pre-commit run --all-files
```

| Hook | Checks |
|---|---|
| `ruff-check`, `ruff-format` | Python lint and formatting (config in `pyproject.toml`) |
| `shellcheck` | shell scripts |
| `markdownlint-cli2` | Markdown (config in `.markdownlint-cli2.yaml`) |
| `actionlint` | GitHub Actions workflows |
| `workflow-permissions` | workflows grant no write scope at the top level and pin each action to a version tag (`tools/check-workflows.py`) |
| `codespell (typos)` | common misspellings everywhere |
| `codespell (British English)` | American spellings in `.md`, `.dsp` and `.lib` files (word list in `tools/en-gb.codespell`) |
| `faust-compile` | every `src/*.dsp` compiles (needs `faust`) |
| `reuse` | every file has a machine-readable licence (SPDX header or `REUSE.toml`) |
| `no-generated-files` | nothing from `build/` or `tests/out/` is committed |
| `no-trademarks` | no manufacturer or product name (list in `tools/trademarks.txt`) in file names, `src/` or `tests/` |
| whitespace, YAML/TOML, shebangs, large files | general hygiene |

GitHub Actions (`.github/workflows/ci.yml`) runs the same hooks, then builds every effect in an Arch Linux container and runs `make lv2 lint test describe`. A second job runs `make vst3 pluginval` and uploads the bundles as the `vst3` artifact, and a third runs `make clap clap-validate` and uploads the plugins as the `clap` artifact. The plots, CSV data and WAV renders from `tests/out/` are uploaded as the `test-output` artifact of each run. Each effect's JSON description and block diagram are uploaded as the `describe` artifact.

### Documentation site

The site at <https://joe-heffer.github.io/faust-pedalkit/> is built from `docs/` with [MkDocs](https://www.mkdocs.org/) and the Material theme, embeds the plots and CSV data from `make test` and the schematic sheets from `make schematics`, and publishes the browser demo from `make web` as `demo/`. `.github/workflows/docs.yml` builds it in the docs image (`Dockerfile.docs`, which adds KiCad, Node.js and MkDocs) and rebuilds and deploys it on every push to `main`. To build it locally:

```sh
python -m venv .venv && .venv/bin/pip install -r tools/docs-requirements.txt
make test web schematics docs MKDOCS=.venv/bin/mkdocs  # build/site/ (schematics need kicad-cli)
make docs-serve MKDOCS=.venv/bin/mkdocs                 # preview at http://127.0.0.1:8000/
```

## Loading in a host

All three hosts below find plugins in `~/.lv2` once `make install` has run. For the VST3 version, run `make install-vst3`, which copies the bundles to `~/.vst3`, the standard per-user VST3 folder on Linux. REAPER, Bitwig, Ardour and Carla scan it, so "BassDrive" and "BassPreamp" then appear in their VST3 lists. For CLAP, run `make install-clap`, which copies the plugins to `~/.clap`, the per-user CLAP folder on Linux that REAPER, Bitwig and Carla scan.

**Ardour.** Ardour scans `~/.lv2` at start-up. If it was already open, use *Window → Plugin Manager → Re-scan*. On a bass track's mixer strip, right-click the processor box, choose *New Plugin → Plugin Selector…*, search for "BassDrive" (or "BassPreamp") and add it.

**REAPER (Linux).** The [REAPER guide](docs/usage/reaper.md) covers input level, latency and presets in more detail.

1. Go to *Options → Preferences → Plug-ins → LV2*. Check that `~/.lv2` is in the path list, then click *Re-scan*.
2. Open the track's FX window, choose *Add*, and find "BassDrive" or "BassPreamp" under *LV2*.
3. Both plugins are mono. On a stereo track, REAPER feeds it channel 1, so record bass on a mono track or set the plugin's pin connector.

**Carla.**

1. Open *Settings → Configure Carla → Paths → LV2* and check that `~/.lv2` is listed.
2. Click *Add Plugin*, then *Refresh* with LV2 ticked.
3. Pick "BassDrive". In the patchbay, connect your audio input to it and it to the system outputs.

## BassDrive controls

| Control | Range | Default | What it does |
|---|---|---|---|
| Level | −40 to +12 dB | 0 dB | Output level |
| Balance | 0 to 100 % | 50 % | 0 = clean only, 100 = driven only. The clean path is full-range, so the low end holds up as Gain rises. |
| Gain | 0 to 100 % | 50 % | Drive amount (audio taper) |
| Bass | −12 to +12 dB | 0 dB | Peaking band at 110 Hz |
| Treble | −15 to +15 dB | 0 dB | High shelf from 2.5 kHz |

Every control is smoothed, so automating or turning them does not zipper. The plugin also has a read-only *Latency* output (32 samples) for the host's delay compensation.

**Signal path:** input DC blocker → split into clean and driven paths. The driven path runs pre-emphasis gain (stage 1), then the 4x-oversampled asymmetric clipper, then a DC blocker and a 5 kHz low-pass. The two paths meet at the Balance blend → Bass → fixed −6 dB mid scoop at 350 Hz → Treble → Level → safety limiter (at most −0.1 dBFS). The design reasoning is in [the circuit notes](docs/bassdrive/circuit-notes.md).

**Using it like the original:** the original's High control is already about +10 dB at noon. For that voicing, start from Treble +10 dB. Here 0 dB on Bass and Treble is flat, apart from the fixed mid scoop.

## Measured behaviour

From `make test` at 48 kHz. The plots (SVG) and the data behind them (CSV) are in `tests/out/bassdrive/`.

- **Silence in gives silence out.** The output stays below −120 dBFS at all 48 combinations of extreme settings.
- **Peak level.** With every control at maximum and 0 dBFS square waves, noise, sweeps or impulses in, the worst sample is −0.10 dBFS.
- **The low end holds up.** At Balance 50 %, the low E fundamental (41 Hz) varies by only 1.4 dB across the whole Gain range. The clean path alone is flat within ±1.5 dB from 30 to 100 Hz.
- **Harmonics** (single sines, driven path only):

  | Gain | 41 Hz THD | 110 Hz THD | Character |
  |---|---|---|---|
  | 0 % | 2.2 % | 1.4 % | light, odd-order |
  | 50 % | 5.9 % | 12.5 % | H2 overtakes H3 at 110 Hz (warm, even-leaning) |
  | 100 % | 30.5 % | 27.5 % | heavy, odd-order dominant, harmonics strong up to the 10th |

- **Frequency response of the driven path.** It rises from about 300 Hz to a broad peak at 1–3 kHz, and the peak grows with Gain (about +3 dB at Gain 0, +25 dB at noon, +36 dB at maximum for small signals). It then falls steeply above about 5 kHz. This is the treble-forward, "grind on top of the clean low end" voicing the original is known for.
- **Fixed mid scoop.** About 5–6 dB at 350 Hz, matching the published measurement of the original.
- **Aliasing.** Against a 1x build of the same DSP, 4x oversampling lowers the worst alias by 22 dB for a 3.7 kHz tone and by 30 dB for a 1.1 kHz tone at full Gain. The worst alias at 1.1 kHz is −65 dBc.

## What to tune by ear

These are measured approximations, not listening-tested. Each item below names the control or `src/bassdrive.dsp` constant to change.

1. **The blend notch.** With Balance near 50 % and Gain high, the two paths cancel at about 6–8 kHz. Listen for a hollow or phasey top end. `postLP` moves it, and `drvTrim` changes its depth.
2. **How lopsided the drive is.** `ledNeg` (−0.8 V) and `negKnee` (6) set how quickly the sound turns warm and even-order as Gain rises. Raise `ledNeg` towards 1.7 for a more symmetric, harder sound.
3. **Overall drive range.** `stage2G` (3.0) and the 303 in `hfGain` set how much distortion there is at each Gain position.
4. **The mid scoop.** `scoopDB` (−6 dB). Try −3 dB for a fuller mix sound, or 0 to remove it.
5. **Fizz.** `postLP` (5 kHz) and Treble. If high Gain sounds buzzy, lower `postLP` towards 3.5 kHz.
6. **Clean/driven loudness.** `drvTrim` (0.28). Set it so that sweeping Balance at your usual Gain doesn't change the perceived volume.
7. **Input level.** The model treats 0 dBFS as 1 V at the pedal's input. If your interface records the bass hot or quiet, every Gain setting will feel shifted, so adjust your input gain before changing the constants.

## Known limitations

- **It isn't a full circuit simulation.** The drive stage is modelled as linear filters around a memoryless waveshaper (static nonlinearity). Effects that depend on the circuit's history are not captured: bias shifting under heavy playing, supply sag, and interaction between the clipper and the filters around it. Fast transients therefore compress a little more neatly than real hardware does.
- **Several values are educated guesses.** These are the Gain pot taper and range, the stage-2 gain, the clipping asymmetry and the post-filter. Each one is marked as "chosen" in the circuit notes, and all are named constants near the top of `src/bassdrive.dsp`.
- **The tone stack doesn't interact.** The EQ bands are independent digital filters, whereas a passive or active network would interact.
- **Latency.** The oversampler adds 32 samples (0.67 ms at 48 kHz). It is compensated inside the plugin between the clean and driven paths, and reported to the host (through an LV2 latency port, the VST3 latency call or the CLAP latency extension), so hosts that support plugin delay compensation will line the track up.
- **Mono only.**
- **Some aliasing remains.** At extreme Gain with very high-pitched material, some aliasing remains despite the 4x oversampling. The safety limiter runs at the base rate and can alias if you drive it hard with Level.

## BassPreamp controls

| Control | Range | Default | What it does |
|---|---|---|---|
| Level | −40 to +12 dB | 0 dB | Output level. 0 dB is unity gain at Blend 0 with a flat EQ. |
| Blend | 0 to 100 % | 50 % | 0 = clean only, 100 = preamp only. Below about 34 Hz the clean signal always passes, as on the hardware. |
| Drive | 0 to 100 % | 50 % | Gain of the drive stage, 12.5 to 40 dB (log-uniform). Audible breakup starts around noon at −12 dBFS input. |
| Presence | 0 to 100 % | 50 % | Boost-only upper-mid/treble gain ahead of the drive stage, so it also adds bite to the distortion |
| Bass | −12 to +12 dB | 0 dB | Low shelf at 80 Hz (40 Hz with Bass Shift) |
| Mid | −12 to +12 dB | 0 dB | Peaking band at 500 Hz (1 kHz with Mid Shift) |
| Treble | −12 to +12 dB | 0 dB | High shelf at 2.8 kHz |
| Bass Shift | off/on | off | Moves Bass from 80 Hz to 40 Hz, for 5- and 6-string basses |
| Mid Shift | off/on | off | Moves Mid from 500 Hz to 1 kHz |
| Cab Bypass | off/on | off | Removes the fixed speaker voicing from the preamp path, for a real cabinet or an impulse response. Not on the hardware. |

Every control is smoothed, including the switches: the shifts glide the band frequency rather than jumping, and Cab Bypass crossfades. The plugin reports 64 samples of latency (two 4x-oversampled clipping stages).

### BassPreamp: presets

The LV2, VST3 and CLAP plugins all ship with the same factory presets, which hosts list in their preset menu (REAPER's preset box, Ardour's and Carla's preset lists, or `jalv`'s `presets` command). VST3 hosts see them as the plugin's program list, and CLAP hosts through preset discovery. They are starting points, chosen by measurement rather than by ear. Each one sets every control, and Level is set so that a −12 dBFS plucked bass line comes out within 0.25 dB of "Clean DI" (K-weighted), so switching presets doesn't jump in loudness.

| Preset | Level | Blend | Drive | Presence | Bass | Mid | Treble | Shifts | Idea |
|---|---|---|---|---|---|---|---|---|---|
| Clean DI | 0 | 0 | 0 | 50 | 0 | 0 | 0 | | Clean path, flat EQ. The level reference. |
| Warm Blend | +0.2 | 40 | 35 | 40 | +2 | 0 | −2 | | Some preamp under the clean signal |
| Growl | −2.5 | 70 | 65 | 60 | +2 | +4 | 0 | Mid | Audible breakup with a 1 kHz lift |
| Grind | −8.5 | 100 | 90 | 70 | +3 | +3 | +2 | | Preamp only. Mid fills the voicing's fixed dip near 450 Hz. |
| Scooped Slap | −1 | 25 | 20 | 70 | +5 | −6 | +6 | | For slap and pop |
| Low B Thump | +0.5 | 35 | 40 | 40 | +4 | −2 | −3 | Bass | 40 Hz shelf for five- and six-string basses |
| Dark Dub | −1.5 | 45 | 25 | 20 | +6 | +2 | −9 | | Heavy lows, little treble |

Levels are in dB and Blend, Drive and Presence in %. The presets live in `src/basspreamp.presets.toml`. Edit that file and run `make lv2 test FX=basspreamp`: the build checks that every preset sets every control within its range, and `test_presets.py` re-measures loudness and peak level.

**Signal path:** input DC blocker → split into clean and preamp paths. The preamp path, following a public schematic of the earlier hardware version, runs:

1. a bass-weighted input network
2. the Presence gain stage, with 4x-oversampled op-amp rail clipping
3. the Drive gain stage, also with 4x-oversampled rail clipping
4. the fixed "speaker" voicing: two Sallen-Key low-passes, one with a shelf leg, and a bridged-T notch at 424 Hz. Cab Bypass (not on the hardware) replaces it with a −11 dB trim, for use with a real cabinet or an impulse response.

The two paths meet at Blend, which models the hardware's capacitor-coupled pot exactly. Then come Bass, Mid, Treble, Level and the safety limiter (at most −0.1 dBFS). The design reasoning is in [the circuit notes](docs/basspreamp/circuit-notes.md).

### BassPreamp: measured behaviour

From `make test FX=basspreamp` at 48 kHz. The plots are in `tests/out/basspreamp/`.

- **Silence in gives silence out.** The output stays below −120 dBFS at all 96 combinations of extreme settings, including both switch positions.
- **Peak level.** With every control at maximum and 0 dBFS square waves, noise, sweeps or impulses in, the worst sample is −0.10 dBFS.
- **EQ.** Blend 0 with a flat EQ is flat within ±0.16 dB from 30 Hz to 15 kHz. The Mid peak sits within 1 % of 500 Hz and 1 kHz at exactly ±12.0 dB. Bass reaches +9.3 dB at 80 Hz and +11.8 dB at 27 Hz, or +8.8 dB at 40 Hz with Bass Shift. Treble reaches +9.1 dB at 2.8 kHz and +11.9 dB at 12 kHz.
- **Preamp voicing.** Small-signal, the preamp path has a bass hump around 100 Hz, a dip around 450–500 Hz and a second hump near 1 kHz. It rolls off steeply above about 3 kHz and is 57 dB below its peak at 12 kHz. Presence adds up to 21.5 dB in the 1–3 kHz range and never cuts.
- **Cab Bypass.** Bypassed, the preamp path peaks broadly near 500 Hz and is 37 dB below its peak at 12 kHz instead of 57 dB. The 100 Hz hump goes, and a dip of about −10 dB appears near 45 Hz at Blend 100 %. On a −12 dBFS bass line it is within 0.5 dB of the voiced loudness at Drive 50 %, and within 1.7 dB across Drive.
- **Harmonics** (single sines at −12 dBFS, preamp path only):

  | Drive | 41 Hz THD | 110 Hz THD | Character |
  |---|---|---|---|
  | 0 % | < 0.01 % | < 0.01 % | clean |
  | 50 % | 0.4 % | 1.9 % | light, odd-order |
  | 100 % | 18.8 % | 8.7 % | heavy, odd-order. H2 grows with Drive (−35 dBc at 41 Hz). |

- **The low end holds up.** At Blend 50 %, the low E fundamental rises by 5.2 dB from Drive 0 to 100 %, and never drops.
- **Presets.** All seven are within 0.25 dB of "Clean DI" in K-weighted loudness on a −12 dBFS bass line. With a 0 dBFS 41 Hz square wave in, none peaks above −0.10 dBFS.
- **Aliasing.** Against a 1x build, 4x oversampling lowers the worst alias by 59 dB for a 3.7 kHz tone and by 68 dB for a 1.1 kHz tone at full Drive and Presence. The worst alias at 1.1 kHz is −113 dBc.

### BassPreamp: what to tune by ear

These are measured approximations, not listening-tested. Each item names the control or the `src/basspreamp.dsp` constant to change.

1. **Input level first.** Like BassDrive, 0 dBFS is treated as 1 V at the input. If Drive 50 % sounds too clean or too dirty, check your interface gain before changing constants.
2. **Clipping character.** `railN` (5) sets how hard the op-amp rail clipping is. Lower values are softer and more "tube-like". `vos` (2 mV) sets the asymmetry, and so how much H2 appears as Drive rises.
3. **Drive and Presence taper.** The `pow(...)` laws in `RgPres` and `driveG` set how the controls spread. The real pots are linear, and the hardware bunches the action near the end.
4. **Clean/preamp loudness.** `drvTrim` (0.32). Set it so that sweeping Blend at your usual Drive doesn't change the perceived volume.
5. **The blend notch.** At Blend around 50 % and high Drive, the paths cancel near 2.5 kHz. Listen for a hollow top end. This is a property of the hardware's blend circuit as traced.
6. **EQ shapes.** `midQ` (0.7) and `trebF` (2.8 kHz) are choices, and so is the use of shelves for Bass and Treble.
7. **Presets.** Every setting in `src/basspreamp.presets.toml` is chosen. Check that each preset sounds like its name, and that the loudness match holds with a real bass and your interface gain.
8. **Cab Bypass level.** `bypTrim` (0.28, −11 dB) is matched by K-weighted loudness. Toggle Cab Bypass at your usual settings and adjust it so the level doesn't jump.

### BassPreamp: known limitations

- **It is based on the earlier version's schematic.** No V2 schematic is public. The drive section and speaker voicing follow a DIY trace of the V1, and the V2 EQ follows its published specification. See the circuit notes' open questions.
- **It isn't a full circuit simulation.** Each op-amp stage is a linear filter followed by a memoryless rail clip, so effects such as the feedback capacitors acting while clipped, slew limiting and recovery from overload are not captured.
- **The mixer stage's clipping is left out.** On the hardware, the ×2.2 mixer can clip at high Blend and Drive.
- **The output switches are not modelled:** the −20 dB pad, the +10 dB boost, phantom power and the ground lift.
- **Mono only.** 64 samples of latency (1.3 ms at 48 kHz), reported to the host.

### BassPreamp: listening scenarios

`make test FX=basspreamp` also renders ten realistic settings (clean, warm, grit, heavy, a hot input, low B, slap, extreme EQ and the Blend cancellation case) to `tests/out/basspreamp/scenarios/`. Each has the dry input, the output, an RMS-matched output and an `_ab.wav` that alternates dry and matched, so loudness does not bias the comparison. Measurements (peak, crest factor, spectral centroid, band spectra) are in `scenarios_metrics.csv` and `scenarios_spectra.csv`.

The default source is a synthesised plucked bass. To audition a real clean DI recording instead, save it as `tests/data/bass-di.flac` (or `.wav`), or set `BASS_DI=/path/to/file`. It needs `ffmpeg`, and the output then goes to `scenarios-<file name>/`. Only commit a recording whose licence allows it, and record the source in `docs/`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow and the hard rules (clean-room sources only, no trademarks, British English). New effect ideas are welcome as issues, even rough ones, and [SECURITY.md](SECURITY.md) to report a vulnerability privately. Pull requests show a checklist from `.github/pull_request_template.md`.

## Licence

The code is MIT; see [LICENSE](LICENSE). The documentation under `docs/` (design notes, circuit research and the site) is [CC-BY-4.0](LICENSES/CC-BY-4.0.txt). Every file's licence is machine-readable, following the [REUSE](https://reuse.software/) specification: an SPDX header in each source file, plus `REUSE.toml` for the rest. The VST3 bundles link the MIT-licensed VST3 SDK, so they are MIT too. pluginval, used only as a test tool, is GPL-3.0 and is not distributed with them. The CLAP plugins are built against the MIT-licensed CLAP headers, and clap-validator (a test tool) is MIT as well. The effects are independent designs and models built from public information. They are not affiliated with, or endorsed by, any pedal manufacturer, and no proprietary code was used.
