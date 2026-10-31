# Plan: BassForge, a clean-room model of the modern parallel bass drive

This is a plan for a new effect, written before any notes or DSP. When work starts, its content moves into `docs/bassforge/circuit-notes.md` and `docs/bassforge/design-notes.md`, and this page is deleted. `BassForge` is a working name, chosen to be neutral.

Its companion is [DigSplit](https://github.com/Joe-Heffer/faust-pedalkit/pull/132), the original design built around a crossover that follows playing strength. BassForge leaves that kind of invention to DigSplit. Its job is to capture one well-known sound as faithfully as public sources allow, with digital quality that sets the bar for the repo.

## 1. The aim

The target is the modern heavy bass sound of parallel clean-and-drive bass preamps: a solid, undistorted fundamental under an aggressive, articulate, growling upper register that cuts through a dense mix. The best-known pedals of this kind come from one Finnish maker. Its name and product names appear in this plan only to identify the reference, and they are in `tools/trademarks.txt` so none of them reaches the plugin.

The effect is **modelled** if the public sources in section 3 give enough component values to trace the circuit, and **circuit-inspired** if they don’t, in which case the CMOS stage is designed from datasheets and general analyses. Phase 0 decides which, and the notes say so.

“World class” has to mean something a test can check. This plan sets it as:

* **Faithful controls and voicing.** The same controls, the same switch positions, and EQ bands at the reported frequencies and range.
* **Low end that never collapses.** At any Drive and Blend setting, the low strings keep their weight and phase, with no notch where the clean and driven paths meet.
* **The right harmonic character.** The asymmetric, low-order-rich profile of a CMOS-inverter drive, with less fizz and two-note intermodulation than the repo’s hard-clipping BassGrit.
* **Clean digital behaviour.** Aliasing well below BassGrit’s, CPU and latency inside the repo budgets, and no zipper on any control, switches included.

## 2. What the model makes possible that the hardware does not

AGENTS.md asks every model to say this. The list is kept short on purpose, so the default sound stays the hardware’s:

* switch positions that crossfade, so Grunt and Attack can be changed while playing without a click
* a phase-aligned blend, so the clean and driven paths never cancel in the low end (the hardware’s analogue filters make that a matter of luck)
* the same sound in LV2, VST3 and CLAP, with factory presets
* an optional speaker voicing for direct recording, off by default
* reusable library blocks (the CMOS inverter shaper and a peaking EQ) for the repo’s original designs, DigSplit included

## 3. What public sources say about the reference

All of these are from retailer, distributor, news and forum pages, so they are **reported**, not documented, until the manufacturer’s manuals are checked.

| Claim | Confidence | Source |
|---|---|---|
| The overdrive is CMOS-based | Reported | [3] |
| Controls: Drive, Blend (clean against driven), Level, plus a Grunt and an Attack switch | Reported | [4], [6] |
| Grunt sets one of three bass-boost amounts **before** the clipping stage | Reported | [6] |
| Attack shapes treble before the clipper: Cut, Flat and, on the later model, Boost | Reported | [6] |
| A four-band post EQ: ±12 dB at 100 Hz, 1 kHz, 2.8 kHz and 5 kHz | Reported | [6] |
| The extended model’s mid bands switch between 250, 500 Hz and 1 kHz, and 750 Hz, 1.5 and 3 kHz | Reported, single source | [5] |
| A later revision adds a cab simulation on the direct output | Reported | [6] |
| The circuit’s predecessor was published as a schematic on a forum by the maker’s founder | Reported, second-hand | [1] |
| A DIY kit inspired by the drive-only model has public build documents | Reported | [2] |

No official schematic of the current pedals is public.

## 4. Research to do first (phase 0)

* Find and read the founder’s predecessor schematic [1] and the DIY build documents [2]. Use them for component values and topology only, redrawn in KiCad from the text, never copied as images.
* Read the manufacturer’s own manuals to confirm the controls, switch positions and EQ frequencies, and to upgrade claims from reported to documented.
* Collect public analyses of CMOS-inverter overdrives (unbuffered CD4049UB and CD4069UB used as linear amplifiers, as in well-known DIY designs) and the datasheet transfer curves, for the shaper’s shape, its gain and its dependence on supply voltage.
* Look for published measurements of the pedals (frequency response at each switch position, harmonic spectra) to use as targets. Measurements of the hardware are fair game; any plugin or firmware is not.
* Add newly met product names (for example `B3K`, `B7K`, `B7K Ultra`) to `tools/trademarks.txt` before they appear anywhere in `docs/`.

## 5. Block diagram

```text
in → DC block (5 Hz) ─┬────── clean path: phase-match all-pass → @(latency) ──────┐
                      │                                                           ├→ Blend → 4-band EQ
                      └→ Drive gain → Grunt (3 positions, crossfaded)             │   → speaker voicing (opt.)
                         → Attack (3 positions, crossfaded)                       │   → Level → pk.safety(0.989) → out
                         → 4x OS [CMOS inverter stages] → post low-pass ──────────┘
```

As on the hardware, the EQ comes after the blend and acts on both paths (inferred from the control layout; phase 0 should confirm it).

| Block | New or reused |
|---|---|
| DC blocker | Reused, `fi.dcblockerat(5)` |
| Grunt and Attack networks | New: the circuit’s filters if phase 0 finds them, otherwise shelves (`pk.lowShelf2`, `pk.highShelf2`) at chosen corners. Each switch computes all three positions and crossfades between them with smoothed weights, as BassPreamp’s Bass Shift does |
| CMOS inverter shaper | New in `pedalkit.lib`: `cmosInv(vdd, gain)`, memoryless and asymmetric, fitted to datasheet transfer curves |
| 4x oversampling | Reused, `pk.oversample4` |
| Phase-match all-pass | New in the effect file: matches the low-frequency phase of the driven path’s filters, so the small-signal sum has no notch |
| Four-band EQ | Reused shelves, plus a new `peak2(g, f, q)` in `pedalkit.lib` for the two mids |
| Speaker voicing | Reused from BassPreamp, with a smoothed on/off |
| Safety limiter | Reused, `pk.safety(0.989)` |

**Latency.** If the CMOS stages need a filter between them, they need two oversamplers (64 samples). That is inside the 128-sample budget. Phase 3 tries a single composite shaper first (32 samples). The bargraph and the dry delay come from one constant, `latencySamples`.

## 6. Draft controls

The order is fixed once released. The labels are neutral, and the switch positions follow the reported hardware.

| # | Label | Unit | Range | Default | Purpose |
|---|---|---|---|---|---|
| 0 | Drive | % | 0 to 100 | 50 | Gain into the CMOS stages |
| 1 | Blend | % | 0 to 100 | 50 | 0 is clean only, 100 is driven only |
| 2 | Level | dB | −40 to +12 | 0 | Output level |
| 3 | Low Boost | position | 0, 1, 2 | 1 | Pre-clip bass boost, three positions (reported) |
| 4 | Attack | position | 0, 1, 2 | 1 | Pre-clip treble: cut, flat, boost (reported) |
| 5 | Bass | dB | −12 to +12 | 0 | Post-blend shelf at 100 Hz (reported) |
| 6 | Low Mid | dB | −12 to +12 | 0 | Post-blend peak at 1 kHz (reported) |
| 7 | High Mid | dB | −12 to +12 | 0 | Post-blend peak at 2.8 kHz (reported) |
| 8 | Treble | dB | −12 to +12 | 0 | Post-blend shelf at 5 kHz (reported) |
| 9 | Speaker | position | off, on | off | Speaker voicing, crossfaded (not on the drive-only hardware) |

The extended model’s switchable mid frequencies can be appended in 0.2.0 as controls 10 and 11, which needs no renumbering. The amount of boost or cut at each switch position is **inferred** or **chosen** until phase 0 finds circuit values.

## 7. Measurable targets

These become `tests/bassforge/test_targets.py`, beside the minimum set and `tests/common/`. Where a target compares with BassGrit, it is there so the claim of better can be measured.

1. **EQ matches the reported spec.** Each band reaches ±12 dB within 0.5 dB at its reported centre frequency (100 Hz, 1 kHz, 2.8 kHz, 5 kHz), and the response is flat within 0.3 dB with all four at 0 dB.
2. **Switch positions are ordered and distinct.** At small signal, Low Boost raises the 60 Hz pre-clip gain in two steps of at least 3 dB each. Attack moves the 3 kHz pre-clip gain from below Flat (Cut) to above it (Boost), each by at least 3 dB.
3. **The switches act before the clipper.** At Drive 70, Low Boost position 2 raises the low-band harmonic content (on a 60 Hz tone) by at least 6 dB more than the same boost applied after the drive would.
4. **Switching is click-free.** `tests/common/test_zipper.py` passes for Low Boost, Attack and Speaker as well as the sliders.
5. **Phase-coherent blend.** At −40 dBFS, where the shaper is near linear, the response from 30 Hz to 8 kHz at Blend 0, 50 and 100 has no dip deeper than 1 dB below the smooth average.
6. **The fundamental survives.** At Blend 50 and Drive 100, a 41 Hz and a 31 Hz tone at −12 dBFS keep their fundamental within 3 dB of the Drive 0 level.
7. **CMOS harmonic profile.** At Drive 50, H2 is within 10 dB of H3, and harmonics above H9 fall by at least 12 dB per octave. If phase 0 finds published spectra of the hardware, the profile is compared with those instead.
8. **Intermodulation.** A fifth on the low strings (41.2 Hz plus 61.7 Hz), at the same upper-band THD as BassGrit, gives at least 6 dB less low-frequency IMD.
9. **Cleanup curve.** `harmonic_trajectory` from −40 to 0 dBFS at Drive 50 is monotonic, and THD passes 1 % between −30 and −18 dBFS.
10. **Aliasing.** At Drive 100, the worst alias for a 1.1 kHz tone is below −60 dBc with 4x oversampling, against BassGrit’s −45.8 dBc.
11. **Loudness.** Every preset is within 1 LU of the others.

## 8. Work plan

Each phase ends with a commit to this PR. The PR stays a draft until phase 7 passes.

* **Phase 0: research.** Section 4. Output: a source list, trademark additions, and the decision between modelled and circuit-inspired.
* **Phase 1: notes.** `docs/bassforge/circuit-notes.md` (the CMOS stage, the Grunt and Attack networks and the EQ, with values, corner frequencies and confidence) and a short `docs/bassforge/design-notes.md` for section 2’s departures. This plan page is then deleted.
* **Phase 2: library.** Add `cmosInv` and `peak2` to `src/lib/pedalkit.lib`, documented in `AGENTS.md` and `docs/development/pedalkit-lib.md`.
* **Phase 3: DSP.** `src/bassforge.dsp`, version 0.1.0, `lv2class "DistortionPlugin"`.
* **Phase 4: tests.** The minimum set (`test_silence`, `test_peak`, `test_freqresp`, `test_harmonics`, the `RENDER_1X` aliasing comparison), `test_targets.py`, `test_dynamics.py` and `test_presets.py`. Plots as SVG, numbers as CSV.
* **Phase 5: presets.** `src/bassforge.presets.toml`, with every control set: a hardware-default setting, a modern metal setting, a fingerstyle grit setting and a clean-heavy blend.
* **Phase 6: docs and schematic.** `docs/bassforge/index.md` with the download marker, the changelog with `## [0.1.0]`, rows in the README, `docs/index.md` and `docs/effects/index.md`, the `mkdocs.yml` nav, and `tools/schematics/bassforge.py` for the modelled circuit.
* **Phase 7: checks.** `make lv2 lint test`, `make vst3 pluginval`, `make clap clap-validate`, `make test web schematics docs` and `make check`, all with `FX=bassforge`. Read every plot, then mark the PR ready.

## 9. What only listening can decide

* The boost and cut at each Low Boost and Attack position, if phase 0 finds no circuit values.
* Whether one CMOS stage or two gives the right growl.
* The Drive taper, and where the drive starts to break up.
* Whether the speaker voicing helps or should go.

## 10. Risks

* **Sourcing.** If the founder’s schematic cannot be found or used, the effect is circuit-inspired, and its sound is matched to reported behaviour instead of traced from components. The plan stays the same; the confidence levels drop.
* **Calibration without hardware.** With no pedal to measure, “faithful” rests on public measurements and descriptions. The notes must say how close that can get.

## Sources

1. Fractal Audio forum, a user’s report of the predecessor schematic. <https://forum.fractalaudio.com/threads/fractal-audio-drive-models-blackglass-7k-based-on-darkglass-microtubes-b7k.132521/>
2. PCBGuitarMania, *Black Mirror* build documents (a DIY kit inspired by the drive-only model). <https://pcbguitarmania.com/wp-content/uploads/2018/06/Black-Mirror-Building-Docs.pdf>
3. Shimamura (Japanese distributor), product article describing the drive-only model as CMOS-based. <https://www.shimamura.co.jp/update/?p=3600>
4. Kirstein, retailer listing for the drive-only model. <https://www.kirstein.de/Spezielle-Basseffekte/Darkglass-Microtubes-B3K.html>
5. No Treble, announcement of the extended model, with its switchable mid frequencies. <https://www.notreble.com/?p=41909>
6. Guitar Center, retailer listing for the extended model (controls and EQ bands). <https://www.guitarcenter.com/Darkglass/Microtubes-B7K-Ultra-V2-Bass-Preamp-Pedal-Aux-In-1500000317420.gc>
