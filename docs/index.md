# Faust Pedal Kit

Clean-room models of classic guitar and bass pedals. They are written in [Faust](https://faust.grame.fr/), built as native Linux [LV2](https://lv2plug.in/) plugins, and checked by offline measurement tests.

Each effect is one Faust file. It comes with research notes that say where every circuit value came from, and with tests that render signals through the compiled DSP and check the results numerically: silence, peak level, frequency response, harmonics and aliasing.

[Install and build](install.md){ .md-button .md-button--primary }
[Browse the effects](effects/index.md){ .md-button }

## Effects

| Effect | What it is | Pages |
|---|---|---|
| **BassDrive** | Bass overdrive with a clean/driven blend and a two-band EQ, modelled on a classic compact bass overdrive pedal | [controls and measurements](bassdrive/index.md) · [circuit notes](bassdrive/circuit-notes.md) |

## Quick start

On Arch (other distributions are covered in [Install and build](install.md)):

```sh
sudo pacman -S --needed faust boost gcc lv2 jalv
git clone https://github.com/Joe-Heffer/faust-pedalkit.git
cd faust-pedalkit
make lv2 install
jalv urn:pedalkit/bassdrive
```

The plugins install into `~/.lv2`, where Ardour, REAPER, Carla and other LV2 hosts find them. See [Loading in a host](hosts.md).

## How the models are made

**Clean-room.** Every model is built from public schematics, circuit analyses, measurements, reviews and manuals. No proprietary plugin, binary or firmware is decompiled, disassembled or used as a reference.

**Every value has a confidence level.** The circuit notes mark each component value and design decision as one of:

| Level | Meaning |
|---|---|
| Documented | Stated by the manufacturer |
| Reported | Stated by one or more third parties, such as a forum post, review or measurement |
| Inferred | Reasoned from the reported facts |
| Chosen | A free modelling choice where no source gives a value |

The "chosen" values are named constants at the top of each `.dsp` file, so you can retune them.

**Measured, not listened to.** The models are judged by measurement: harmonics, frequency response, aliasing and levels. Each effect page shows the current measurements and lists the constants a human should tune by ear.

**Neutral names.** Plugins carry no manufacturer branding. Product names appear in the docs only to identify the reference hardware.

## Licence

The code is MIT and the documentation is CC BY 4.0. See [About](about.md) for details and how to cite the project.
