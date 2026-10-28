# Faust Pedal Kit

<img src="docs/assets/logo-wordmark.svg" alt="Pedal Kit logo: a pedal with a sine wave going in and a clipped wave coming out" width="360">

[![CI](https://github.com/Joe-Heffer/faust-pedalkit/actions/workflows/ci.yml/badge.svg)](https://github.com/Joe-Heffer/faust-pedalkit/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/Joe-Heffer/faust-pedalkit?include_prereleases&sort=semver)](https://github.com/Joe-Heffer/faust-pedalkit/releases)

A workshop for designing new guitar and bass effects in Faust: new sounds, and new kinds of effect, built as native Linux LV2, VST3 and CLAP plugins and checked by offline measurement tests.

> [!NOTE]
> Please [**read the documentation**](https://joe-heffer.github.io/faust-pedalkit/) for each effect's controls, design and circuit research, and current measurement plots.

[Faust](https://faust.grame.fr/) makes it cheap to try ideas a box of components can't easily be: clippers whose shape follows the playing, filters that track pitch, stages that never share a circuit board. Each effect is compiled to an LV2, a VST3 and a CLAP plugin, with an optional standalone JACK build, and has offline tests that render signals and check them numerically, so a new idea is measured before anyone has to trust their ears.

> [!TIP]
> New to DSP or Faust? [How it works](docs/development/how-it-works.md) explains what an effect is in code, how Faust describes it, and how one `.dsp` file becomes LV2, VST3 and CLAP plugins plus measurements. [Adding an effect](docs/development/adding-an-effect.md) is the step-by-step workflow.

Studying classic hardware is part of the method rather than the goal. Clean-room models of well-known pedals show how they get their character, calibrate the measurement tools against something known, and supply tested building blocks (clippers, analogue filter sections, voicings) for original designs to reuse, bend and recombine. Each effect is one of:

- **Original:** a sonic idea with no single reference device, written up in design notes.
- **Circuit-inspired:** a real circuit deliberately taken somewhere it couldn't go.
- **Modelled:** a measured, sourced model of one device, written up in circuit notes.

Two of the four effects so far are models. Original and circuit-inspired effects are where the project is heading: see [Designing new sounds](docs/development/designing-new-sounds.md).

| Effect | Kind | Description | Notes |
|---|---|---|---|
| **BassDrive** (`src/bassdrive.dsp`) | Modelled | Bass overdrive with clean/driven blend and two-band EQ, modelled on a classic compact bass overdrive pedal | [circuit notes](docs/bassdrive/circuit-notes.md) |
| **BassPreamp** (`src/basspreamp.dsp`) | Modelled | Tube-voiced bass preamp/DI with blend, presence, built-in speaker voicing and three-band EQ with shiftable bass and mid, modelled on a classic bass preamp/DI pedal | [circuit notes](docs/basspreamp/circuit-notes.md) |
| **BassGrit** (`src/bassgrit.dsp`) | Circuit-inspired | Hard-clipping op-amp distortion for bass (Distortion, Filter, Level, Low Blend, Crossover) with a 4th-order split that keeps the low band clean | [circuit notes](docs/bassgrit/circuit-notes.md), [design notes](docs/bassgrit/design-notes.md) |
| **BassEras** (`src/basseras.dsp`) | Circuit-inspired | Bass preamp/DI whose Character knob sweeps the pre-clip EQ, the gain and a bias bloom on hard notes, with Blend, Drive, Bite, Cab Bypass and a Low/Mid/High EQ | [circuit notes](docs/basseras/circuit-notes.md), [design notes](docs/basseras/design-notes.md) |
| **MidHump** (`src/midhump.dsp`) | Circuit-inspired | Mid-hump overdrive (Drive, Tone, Level) with an optional full-range clean Blend and a Bloom (bias shift) control that the original circuit lacks | [circuit notes](docs/midhump/circuit-notes.md), [design notes](docs/midhump/design-notes.md) |

> [!NOTE]
> To hear them without installing anything, open the [browser demo](https://joe-heffer.github.io/faust-pedalkit/demo/): the same Faust code compiled to WebAssembly, with a test riff, an audio file or live input ([how it works](docs/usage/browser.md)).

## Install

Each effect is released on its own. Download its tarball from the [releases page](https://github.com/Joe-Heffer/faust-pedalkit/releases) (tagged `<name>-v<version>`), unpack it and run its installer:

```sh
tar -xzf bassdrive-*-linux-x86_64.tar.gz
cd bassdrive-*-linux-x86_64
./install.sh          # copies the LV2, VST3 and CLAP plugins into ~/.lv2, ~/.vst3 and ~/.clap
```

Then rescan plugins in your DAW. `./install.sh --help` lists the options, including `--uninstall`. The release plugins need x86_64 Linux with glibc 2.35 or newer (Ubuntu 22.04, Debian 12 or later). See [Install and build](https://joe-heffer.github.io/faust-pedalkit/install/) for details, or read on to build from source.

## Build from source

```sh
git clone https://github.com/Joe-Heffer/faust-pedalkit.git
cd faust-pedalkit
make lv2 lint test        # build the LV2 plugins, lint them and run the offline tests
make vst3 clap            # VST3 and CLAP plugins
make install              # copies the LV2 bundles to ~/.lv2 (install-vst3 and install-clap for the others)
make help                 # every target and effect
```

Add `FX=<name>` to any target to build one effect. The full guide is in the documentation:

- [Install and build](docs/install.md): dependencies for Arch and Debian/Ubuntu, building in a container, VST3 and CLAP, plugin URIs and the repository layout
- [Loading in a host](docs/usage/hosts.md): Ardour, REAPER, Carla and `jalv` ([REAPER guide](docs/usage/reaper.md))
- [Linting and CI](docs/development/ci.md): pre-commit hooks, GitHub Actions and building the documentation site
- [Tests and measurements](docs/development/testing.md)

## Effects in detail

Each effect's controls, presets, signal path, measured behaviour, listening notes and known limitations are on its documentation page:

[BassDrive](docs/bassdrive/index.md) · [BassPreamp](docs/basspreamp/index.md) · [BassGrit](docs/bassgrit/index.md) · [BassEras](docs/basseras/index.md) · [MidHump](docs/midhump/index.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow and the hard rules (clean-room sources only, no trademarks, British English). New effect ideas are welcome as issues, even rough ones, and [SECURITY.md](SECURITY.md) to report a vulnerability privately. Pull requests show a checklist from `.github/pull_request_template.md`.

## Licence

The code is MIT; see [LICENSE](LICENSE). The documentation under `docs/` (design notes, circuit research and the site) is [CC-BY-4.0](LICENSES/CC-BY-4.0.txt). Every file's licence is machine-readable, following the [REUSE](https://reuse.software/) specification: an SPDX header in each source file, plus `REUSE.toml` for the rest. The VST3 bundles link the MIT-licensed VST3 SDK, so they are MIT too. pluginval, used only as a test tool, is GPL-3.0 and is not distributed with them. The CLAP plugins are built against the MIT-licensed CLAP headers, and clap-validator (a test tool) is MIT as well. The effects are independent designs and models built from public information. They are not affiliated with, or endorsed by, any pedal manufacturer, and no proprietary code was used.
