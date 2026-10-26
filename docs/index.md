# Faust Pedal Kit

A workshop for designing new guitar and bass effects: new sounds, and new kinds of effect that a box of components couldn't easily be. The effects are written in [Faust](https://faust.grame.fr/), built as native Linux [LV2](https://lv2plug.in/) and VST3 plugins, and checked by offline measurement tests.

Each effect is one Faust file. It comes with notes that say where every value came from or what it is for, and with tests that render signals through the compiled DSP and check the results numerically: silence, peak level, frequency response, harmonics and aliasing.

Classic hardware is studied here too. Clean-room models of well-known circuits show how they get their character and supply tested building blocks (clippers, analogue filter sections, voicings) that original designs can reuse, bend and recombine. The first two effects are models of this kind; see [Designing new sounds](development/designing-new-sounds.md) for where the project is heading.

[Install and build](install.md){ .md-button .md-button--primary }
[Browse the effects](effects/index.md){ .md-button }
[Try them in your browser](demo/index.html){ .md-button }

## Effects

| Effect | What it is | Pages |
|---|---|---|
| **BassDrive** | Bass overdrive with a clean/driven blend and a two-band EQ, modelled on a classic compact bass overdrive pedal | [controls and measurements](bassdrive/index.md) · [circuit notes](bassdrive/circuit-notes.md) |
| **BassPreamp** | Tube-voiced bass preamp/DI with a clean blend, Presence, built-in speaker voicing and a three-band EQ with shiftable Bass and Mid, modelled on a classic bass preamp/DI pedal | [controls and measurements](basspreamp/index.md) · [circuit notes](basspreamp/circuit-notes.md) |
| **MidHump** | Mid-hump overdrive with Drive, Tone, Level and an optional full-range clean Blend | [controls](midhump/index.md) · [circuit notes](midhump/circuit-notes.md) · [design notes](midhump/design-notes.md) |
| **BassGrit** | Hard-clipping distortion for bass with a clean low band: Distortion, Filter, Level, Low Blend and Crossover | [controls](bassgrit/index.md) · [circuit notes](bassgrit/circuit-notes.md) · [design notes](bassgrit/design-notes.md) |

## Quick start

On Arch (other distributions are covered in [Install and build](install.md)):

```sh
sudo pacman -S --needed faust boost gcc lv2 jalv
git clone https://github.com/Joe-Heffer/faust-pedalkit.git
cd faust-pedalkit
make lv2 install
jalv urn:pedalkit/bassdrive
```

The plugins install into `~/.lv2`, where Ardour, REAPER, Carla and other LV2 hosts find them. See [Loading in a host](usage/hosts.md) and the [REAPER guide](usage/reaper.md).

## How the effects are made

New to DSP or Faust? [How it works](development/how-it-works.md) explains what an effect is in code, how Faust describes it, and how one `.dsp` file becomes LV2, VST3 and CLAP plugins plus measurements.

**Ideas first, models as a means.** An effect is *original* (a sonic idea with no single reference device), *circuit-inspired* (a real circuit taken somewhere it couldn't go), or *modelled* (a measured, sourced model of one device). Original effects are documented in design notes, models in circuit notes.

**Clean-room.** Anything taken from existing hardware is built from public schematics, circuit analyses, measurements, reviews and manuals. No proprietary plugin, binary or firmware is decompiled, disassembled or used as a reference.

**Every value has a confidence level.** The design and circuit notes mark each value and design decision as one of:

| Level | Meaning |
|---|---|
| Documented | Stated by the manufacturer |
| Reported | Stated by one or more third parties, such as a forum post, review or measurement |
| Inferred | Reasoned from the reported facts |
| Chosen | A free design choice, with its intent stated |

The "chosen" values are named constants at the top of each `.dsp` file, so you can retune them.

**Measured, then tuned by ear.** The effects are judged by measurement: harmonics, frequency response, aliasing and levels. Each effect page shows the current measurements and lists the constants a human should tune by ear.

**Neutral names.** Plugins carry no manufacturer branding. Product names appear in the docs only to identify reference or inspiring hardware.

## Licence

The code is MIT and the documentation is CC BY 4.0. See [About](about.md) for details and how to cite the project.
