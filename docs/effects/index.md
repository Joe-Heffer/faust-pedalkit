# Effects

Five effects so far, all mono and all for Linux as CLAP, VST3 and LV2 plugins. Every one can be [played in your browser](../demo/index.html) before you download it.

| Effect | What it sounds like | Type | Latency | Pages |
|---|---|---|---|---|
| **BassDrive** | Grit on top of a solid, clean low end | Bass overdrive | 32 samples | [controls and sound](../bassdrive/index.md) · [circuit notes](../bassdrive/circuit-notes.md) |
| **BassPreamp** | A tube-voiced preamp and DI, ready for the desk, with a three-band EQ | Bass preamp/DI | 64 samples | [controls and sound](../basspreamp/index.md) · [circuit notes](../basspreamp/circuit-notes.md) |
| **MidHump** | Mid-forward overdrive with tight lows and an optional clean blend | Overdrive | 32 samples | [controls and sound](../midhump/index.md) · [circuit notes](../midhump/circuit-notes.md) · [design notes](../midhump/design-notes.md) |
| **BassEras** | One Character knob from deep and scooped to pushed and growling | Bass preamp/DI | 64 samples | [controls and sound](../basseras/index.md) · [circuit notes](../basseras/circuit-notes.md) · [design notes](../basseras/design-notes.md) |
| **BassGrit** | Heavy hard clipping on the upper band, with clean, tight lows | Distortion | 32 samples | [controls and sound](../bassgrit/index.md) · [circuit notes](../bassgrit/circuit-notes.md) · [design notes](../bassgrit/design-notes.md) |

Latency is the fixed delay the effect reports to the host, which compensates for it (32 samples is 0.67 ms at 48 kHz).

## Download

<!-- downloads:all -->

See [Download](../download.md) for which format to use, how to install and what to do if an effect doesn't show up in your DAW.

## What each effect page covers

* **Download** and a link to the browser demo.
* **Controls:** range, default and what each one does.
* **Signal path:** the blocks in order, as implemented in the `.dsp` file.
* **Measured behaviour:** plots from the current `make test` run, with the CSV data behind each one.
* **What to tune by ear:** the named constants a listener should adjust, because the effects are verified by measurement, not by listening.
* **Known limitations.**

Every control is smoothed, so automation and live tweaking do not zipper. The output never exceeds −0.1 dBFS, because each effect ends in a soft safety limiter.

## For developers

Each effect is *original*, *circuit-inspired* or *modelled* (see [Designing new sounds](../development/designing-new-sounds.md)). Design notes record the idea behind an original or circuit-inspired effect: the sound it is after, its prior art, its block diagram, the intent of each constant and the measurable targets its tests check. Circuit notes record the research behind each model: the reference circuit's documented controls, the block diagram, every stage with its component values and corner frequencies, the confidence level of each claim, the sources and the open questions.

The LV2 URI is `urn:pedalkit/<name>` and the CLAP ID `pedalkit.<name>`. To build the plugins yourself, see [Build from source](../install.md).
