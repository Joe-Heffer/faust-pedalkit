---
hide:
  - navigation
  - toc
---

<!-- markdownlint-disable-next-line MD041 -->
<div class="pk-hero" markdown>

![Pedal Kit logo: a pedal with a sine wave going in and a clipped wave coming out](assets/logo-wordmark.svg){ .pk-hero-logo width="320" }

# Free effect plugins for bass and guitar { .pk-hero-title }

Overdrive, distortion and preamps for Linux, as CLAP, VST3 and LV2 plugins. Download one, run the installer and play. There is no account, licence key or root password.
{ .pk-hero-lead }

[Download the effects](download.md){ .md-button .md-button--primary }
[Play them in your browser](demo/index.html){ .md-button }

</div>

## The effects

Each download holds the effect as CLAP, VST3 and LV2 plugins, with an installer, so one file suits any Linux DAW.

<div class="grid cards pk-cards" markdown>

* **BassDrive** · bass overdrive

    ---

    Grit on top, with a solid low end underneath. A clean/driven Balance, Gain, and Bass and Treble controls.

    <!-- download-button:bassdrive -->

    [More about BassDrive](bassdrive/index.md) · [Try it](demo/index.html?fx=bassdrive)

* **BassPreamp** · bass preamp and DI

    ---

    A tube-voiced preamp that you can plug straight into a desk: drive, Presence, a clean blend and a three-band EQ with shiftable Bass and Mid.

    <!-- download-button:basspreamp -->

    [More about BassPreamp](basspreamp/index.md) · [Try it](demo/index.html?fx=basspreamp)

* **MidHump** · overdrive

    ---

    A mid-forward overdrive that keeps the lows tight. Blend brings back the full-range clean sound, and Bloom lets the distortion change as each note rings.

    <!-- download-button:midhump -->

    [More about MidHump](midhump/index.md) · [Try it](demo/index.html?fx=midhump)

* **BassEras** · bass preamp and DI

    ---

    One Character knob takes the preamp from deep and scooped, through flat and warm, to pushed and growling, with hard notes blooming as they ring.

    <!-- download-button:basseras -->

    [More about BassEras](basseras/index.md) · [Try it](demo/index.html?fx=basseras)

* **BassGrit** · distortion

    ---

    Heavy hard-clipping distortion on the upper band only. The lows stay clean and tight, with a Crossover and Low Blend to set how much.

    <!-- download-button:bassgrit -->

    [More about BassGrit](bassgrit/index.md) · [Try it](demo/index.html?fx=bassgrit)

</div>

## Install in three steps

1. **Download** an effect from its card above or from the [Download](download.md) page.
2. **Install** it. Unpack the file, open a terminal in the folder and run `./install.sh`. It copies the plugins into `~/.lv2`, `~/.vst3` and `~/.clap` in your home folder and needs no root.
3. **Play.** Rescan plugins in your DAW and add the effect to a mono track. The [host guides](usage/hosts.md) show where to click in REAPER, Ardour and Carla.

The plugins need 64-bit Linux with glibc 2.35 or newer: Ubuntu 22.04, Debian 12 or later, or any current rolling distribution such as Arch or Fedora.

## Make your own sounds

Every effect here is one short [Faust](https://faust.grame.fr/) file, with notes that say where each value came from and tests that measure the result. The kit is also a workshop for designing new effects.

<div class="grid cards pk-cards" markdown>

* **Design in your browser**

    ---

    Build an effect from blocks, wire them up and hear it straight away, with nothing to install. The designer writes the Faust code for you.

    [Open the effect designer](demo/designer/index.html){ .md-button }

* **Build and change the effects**

    ---

    Build the plugins from source, retune the named constants, or add an effect of your own with its notes, tests and measurements.

    [Start developing](development/index.md){ .md-button }

</div>

[How the effects are made](about.md#how-the-effects-are-made) explains the rules every effect follows: clean-room research, a confidence level for every value, and judging by measurement before tuning by ear.
