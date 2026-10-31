# Plan: DigSplit, a bass drive whose crossover follows the playing

This is a plan for a new **original** effect, written before any notes or DSP. When work starts, its content moves into `docs/digsplit/design-notes.md` and this page is deleted. `DigSplit` is a working name, chosen to be neutral.

## 1. The idea

Split-band bass drives (BassGrit here, and many pedals) keep the low end clean by sending only the band above a fixed crossover into the clipper. The crossover is a compromise. Set it low, and soft notes get full, warm grit but hard notes turn to mud. Set it high, and hard notes stay tight but soft playing sounds thin and fizzy.

DigSplit moves the crossover with playing strength. An envelope of the input sets the crossover frequency, note by note:

* **Dig in** and the crossover rises. More of the note stays clean, so a hard pick stays tight and punchy, and the clipper gets only the upper harmonics.
* **Play softly** and the crossover falls. More of the note goes through the clipper, so quiet playing gets a thicker growl.
* **Over the life of a note**, the envelope decays, so the crossover falls and the note blooms from a clean attack into grit as it sustains.

Two controls set the crossover at the soft and the hard end. If the hard setting is below the soft one, the behaviour inverts: hard playing drives more of the low end, for a player who wants digging in to sound dirtier. One structure gives both feels.

Measured, the idea is a drive whose harmonic content depends on the input level twice: once through the shaper’s curve, as in any drive, and once through the band of the note that reaches the shaper. Section 6 turns that into tests.

## 2. Prior art and inspirations

1. Split-band bass distortion with a fixed crossover: [BassGrit](../../bassgrit/index.md), and parallel clean-low pedals in general.
2. Envelope-controlled filters (auto-wah and envelope filters) move a filter with playing strength, but filter the whole signal instead of choosing what is distorted.
3. Dynamic and multiband compressors move gain per band with level. DigSplit moves the band edge instead of the gain.
4. Zavalishin, *The Art of VA Filter Design*, on topology-preserving transform (TPT) filters, which stay stable and quiet when their cut-off is modulated at audio rate. <https://www.native-instruments.com/fileadmin/ni_media/downloads/pdf/VAFilterDesign_2.1.0.pdf>
5. Linkwitz, “Active crossover networks for noncoincident drivers”, *JAES* 24(1), 1976, for the Linkwitz-Riley alignment whose bands sum to an all-pass.
6. [Designing for feel](../designing-for-feel.md): the `oversample4c` pattern and the envelope measurements used here.

To my knowledge no common effect makes the distortion band edge follow playing strength, but I have not done a wide search. Phase 0 includes one.

## 3. Block diagram

```text
in → DC block (5 Hz) ─┬→ envelope (peak, attack/release, in dB)
                      │        → map to log frequency between Soft Xover and Hard Xover
                      │        → fc (smooth, base rate) ──────┬────────────────┐
                      │                                       ▼                ▼
                      └──────────────────────→ modulated LR4 split ──┬→ low band → @(latency) → × Low Blend ─┐
                                                                     └→ high band → Drive → 4x OS shaper     │
                                                                          → Tone low-pass ───────────────────┤
                                                                                                             ▼
                                                                        sum → Level → pk.safety(0.989) → out
```

| Block | New or reused |
|---|---|
| DC blocker | Reused, `fi.dcblockerat(5)` |
| Envelope follower | New: peak follower with separate attack and release, output in dB. Candidate for `pedalkit.lib` as `envDb(att, rel)`, since BassForge’s Tighten needs the same thing |
| Level-to-frequency map | New: `fc = soft · (hard / soft)^t`, where `t` runs from 0 to 1 as the envelope rises from Sensitivity to Sensitivity + Range, clamped and eased |
| Modulated LR4 split | New in `pedalkit.lib` as `lr4splitv(fc)`. Built from TPT state-variable sections so that a moving `fc` stays stable. The high band is formed as `AP(x) − LP4(x)`, where `AP` is the matching 2nd-order all-pass, so the two bands still sum to that all-pass while `fc` moves |
| Shaper | Reused: `pk.asymSoftHard` inside `pk.oversample4` (memoryless) |
| Tone low-pass | Reused, `fi.lowpass` |
| Low-band latency match | Reused pattern, `@(pk.os4Latency)` |
| Crossover meter | An `hbargraph("Crossover [unit:Hz]", …)` showing the current `fc`, so the player can see what the envelope does |
| Safety limiter | Reused, `pk.safety(0.989)` |

**Latency** is one `pk.os4Latency` (32 samples), well inside the 128-sample budget.

**Why the envelope reads the input, not the band.** If it read the high band, raising the crossover would lower its own input and the loop could oscillate. Reading the full-range input keeps the control path open-loop.

## 4. Draft controls

All values are **chosen** and will be retuned by ear. The order is fixed once released.

| # | Label | Unit | Range | Default | Purpose |
|---|---|---|---|---|---|
| 0 | Drive | % | 0 to 100 | 50 | Gain into the shaper |
| 1 | Tone | % | 0 to 100 | 40 | Post-shaper low-pass, 0 bright and 100 dark |
| 2 | Level | dB | −40 to +12 | 0 | Output level |
| 3 | Low Blend | % | 0 to 100 | 80 | Level of the clean low band |
| 4 | Soft Xover | Hz | 40 to 800 | 80 | Crossover for soft playing |
| 5 | Hard Xover | Hz | 40 to 800 | 300 | Crossover for hard playing (below Soft Xover inverts the feel) |
| 6 | Sensitivity | dB | −50 to 0 | −30 | Input level at which the crossover starts to move |
| 7 | Range | dB | 6 to 40 | 24 | Level span over which it moves from soft to hard |
| 8 | Response | ms | 20 to 1000 | 200 | Envelope release, how fast the crossover falls back after a note |

The envelope attack is a fixed constant, about 3 ms (**chosen**: fast enough to catch a pick before the clipper sees the bulk of the note, slow enough not to follow single cycles of a 41 Hz fundamental). Phase 1 should decide whether it needs a control.

## 5. Constants

| Constant | Value | Confidence | Intent |
|---|---|---|---|
| Envelope attack | 3 ms | Chosen | As above |
| Envelope detector | peak, full-wave | Chosen | Peak follows the pick, which is what players mean by playing strength; RMS would lag it |
| Map easing | smoothstep on `t` | Chosen | No corner in the response where the crossover starts and stops moving |
| `fc` smoothing | one-pole, 2 ms | Chosen | Removes the steps of the envelope’s attack without slowing it |
| Split slope | 4th order (LR4) | Chosen | As in BassGrit, which measured 25 dB more fundamental in the clipper with 2nd order |
| Shaper | `asymSoftHard(1, 0.8, 4)` | Chosen | Some even-order content and a harder negative knee; listening decides |
| Tone range | 400 Hz to 12 kHz | Chosen | Dark enough to tame fizz, bright enough to stay open |
| Level range | −40 to +12 dB | Chosen | As in the other effects |

## 6. Measurable targets

These become `tests/digsplit/test_targets.py` and `test_dynamics.py`, beside the minimum set and `tests/common/`. The numbers are first guesses (**chosen**).

1. **The split sums correctly when static.** With Drive 0, Low Blend 100 and Soft Xover equal to Hard Xover, the response is flat within 0.3 dB from 30 Hz to 8 kHz.
2. **The split stays clean while it moves.** With Drive 0 and Low Blend 100, a 100 Hz tone with a level step that sweeps the crossover from 80 Hz to 400 Hz produces modulation sidebands below −50 dBc. This shows the `AP − LP4` construction keeps the sum intact while `fc` moves.
3. **The crossover follows the level.** The crossover meter (or, if the renderer cannot read bargraphs, the low-band level inferred from the output) moves monotonically from Soft Xover to Hard Xover as a 200 Hz tone rises from Sensitivity to Sensitivity + Range, and stays within 5 % of each end outside that span.
4. **Hard notes stay tight.** At Drive 70, a 41 Hz tone at −6 dBFS has at least 10 dB less THD with the default settings than with Hard Xover set equal to Soft Xover (a fixed 80 Hz split).
5. **Soft notes get grit.** At Drive 70, a 41 Hz tone at −30 dBFS has at least 6 dB more harmonic content in 100 Hz to 1 kHz than with Soft Xover set equal to Hard Xover (a fixed 300 Hz split).
6. **Bloom over a note.** On `pluck` at −6 dBFS, `harmonics_over_time` shows the H3-to-H1 ratio rising by at least 6 dB between the first 50 ms and the 500 to 800 ms window. Inverted (Hard Xover 80, Soft Xover 300), the same ratio falls. This target competes with ordinary cleanup: as the note decays, the shaper also clips less. If the measurement shows cleanup winning at the defaults, the notes say so and Range or Drive is retuned, rather than the target being dropped silently.
7. **Response sets the recovery.** After a −6 dBFS burst, the crossover is back within 10 % of Soft Xover after about 3 × Response, at Response 50 ms and 500 ms.
8. **No pumping on a steady note.** On a sustained 41 Hz tone, the crossover ripples by under 5 % (the release must not follow single cycles).
9. **Aliasing.** The `RENDER_1X` comparison: 4x lowers the worst alias by at least 20 dB at 441 Hz at Drive 100.

## 7. Dynamics and feel

The whole effect is a feel mechanism, so its targets are section 6 (items 3 to 8). In the terms of [Designing for feel](../designing-for-feel.md): it gives an *attack against sustain* difference (item 6) and a *level-dependent EQ* into the clipper (items 4 and 5), with *program-dependent timing* left out of 0.1.0.

## 8. Work plan

Each phase ends with a commit to this PR. The PR stays a draft until phase 6 passes.

* **Phase 0: prior-art search.** Look for published effects with a level-dependent distortion band edge, and cite or distinguish them.
* **Phase 1: notes.** `docs/digsplit/design-notes.md` from this page, then delete the plan.
* **Phase 2: library.** Add `envDb` and `lr4splitv` to `src/lib/pedalkit.lib`, documented in `AGENTS.md` and `docs/development/pedalkit-lib.md`. Check whether BassGrit can use `lr4splitv` with a fixed `fc` without its measured results changing, and move it over if so. Check whether `tests/lib/render-arch.cpp` can report a bargraph over time; if not, add that (it would help every envelope-driven effect).
* **Phase 3: DSP.** `src/digsplit.dsp`, version 0.1.0, `lv2class "DistortionPlugin"`.
* **Phase 4: tests.** The minimum set, the `RENDER_1X` comparison, `test_targets.py`, `test_dynamics.py` and `test_presets.py`. Plots as SVG, numbers as CSV.
* **Phase 5: presets and docs.** `src/digsplit.presets.toml` (tight pick, fingerstyle bloom, inverted “dig for dirt”, and a fixed-split setting for comparison), `docs/digsplit/index.md` with the download marker, the changelog with `## [0.1.0]`, the table rows and the nav. No circuit notes, so no schematic.
* **Phase 6: checks.** `make lv2 lint test`, `make vst3 pluginval`, `make clap clap-validate`, `make test web docs` and `make check`, all with `FX=digsplit`. Read every plot, then mark the PR ready.

## 9. What only listening can decide

* Whether a crossover moving during a note is heard as bloom, or as a filter sweep (a wah-like artefact). If it is a sweep, slow the `fc` smoothing or narrow the default span.
* The default Soft Xover and Hard Xover, and whether five-string players need a lower Soft Xover.
* The Response default, and whether attack also needs a control.
* Whether the inverted mode is useful enough to keep in the presets.

## 10. Risks and relation to BassForge

* **Audible sweep.** The main risk is item 1 of section 9. The fallback is to move the crossover only between notes (a slower envelope), at the cost of the bloom.
* **Modulated filter artefacts.** Covered by target 2. If the TPT sections still produce sidebands, the fallback is to crossfade between two fixed splits, which is cheaper and can’t modulate but gives a coarser control.
* **Overlap with BassForge** (draft PR #131): its Tighten control applies the same idea to a pre-clip shelf. If both land, they share `envDb` and the BassForge notes should point here. Whichever merges second rebases its `mkdocs.yml` nav entry under *Plans*.
