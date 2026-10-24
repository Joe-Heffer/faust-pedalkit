# Effects

| Effect | Type | Reference hardware | Latency | Pages |
|---|---|---|---|---|
| **BassDrive** | Bass overdrive | A classic compact two-band bass overdrive pedal | 32 samples | [controls and measurements](../bassdrive/index.md) · [circuit notes](../bassdrive/circuit-notes.md) |

Every effect page covers:

- **Controls:** range, default and what each one does.
- **Signal path:** the blocks in order, as implemented in the `.dsp` file.
- **Measured behaviour:** plots from the current `make test` run, with the CSV data behind each one.
- **What to tune by ear:** the named constants a listener should adjust, because the models are verified by measurement, not by listening.
- **Known limitations.**

The circuit notes record the research behind each model: the reference pedal's documented controls, the block diagram, every stage with its component values and corner frequencies, the confidence level of each claim, the sources and the open questions.

All effects are mono LV2 plugins with the URI `urn:pedalkit/<name>`. Every control is smoothed, so automation and live tweaking do not zipper. The output never exceeds −0.1 dBFS, because each effect ends in a soft safety limiter.
