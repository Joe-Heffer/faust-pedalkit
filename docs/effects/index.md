# Effects

## Download

<!-- downloads:all -->

The CLAP plugin is the default choice: it is the newest of the three formats and fully open. The tarball holds all three plus an installer, `install.sh`; see [Install a release](../install.md#install-a-release).

## The effects

| Effect | Type | Kind | Latency | Pages |
|---|---|---|---|---|
| **BassDrive** | Bass overdrive | Modelled: a classic compact two-band bass overdrive pedal | 32 samples | [controls and measurements](../bassdrive/index.md) · [circuit notes](../bassdrive/circuit-notes.md) |
| **BassPreamp** | Bass preamp/DI | Modelled: a classic tube-voiced bass preamp/DI pedal | 64 samples | [controls and measurements](../basspreamp/index.md) · [circuit notes](../basspreamp/circuit-notes.md) |
| **MidHump** | Overdrive | Circuit-inspired: a mid-hump overdrive with a clean blend | 32 samples | [controls](../midhump/index.md) · [circuit notes](../midhump/circuit-notes.md) · [design notes](../midhump/design-notes.md) |
| **BassEras** | Bass preamp/DI | Circuit-inspired: a Character knob that sweeps the pre-clip EQ, gain and attack | 64 samples | [controls](../basseras/index.md) · [circuit notes](../basseras/circuit-notes.md) · [design notes](../basseras/design-notes.md) |
| **BassGrit** | Distortion | Circuit-inspired: an op-amp hard-clipping distortion with the low band kept clean | 32 samples | [controls](../bassgrit/index.md) · [circuit notes](../bassgrit/circuit-notes.md) · [design notes](../bassgrit/design-notes.md) |

Every effect page covers:

- **Controls:** range, default and what each one does.
- **Signal path:** the blocks in order, as implemented in the `.dsp` file.
- **Measured behaviour:** plots from the current `make test` run, with the CSV data behind each one.
- **What to tune by ear:** the named constants a listener should adjust, because the models are verified by measurement, not by listening.
- **Known limitations.**

Each effect is *original*, *circuit-inspired* or *modelled* (see [Designing new sounds](../development/designing-new-sounds.md)). The two so far are models; original designs are where the project is heading.

Design notes record the idea behind an original effect: the sound it is after, its prior art, its block diagram, the intent of each constant and the measurable targets its tests check. Circuit notes record the research behind each model: the reference pedal's documented controls, the block diagram, every stage with its component values and corner frequencies, the confidence level of each claim, the sources and the open questions.

All effects are mono LV2 plugins with the URI `urn:pedalkit/<name>`. Every control is smoothed, so automation and live tweaking do not zipper. The output never exceeds −0.1 dBFS, because each effect ends in a soft safety limiter.
