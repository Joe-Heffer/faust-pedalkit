# Plan: BassForge, a modern split-voice bass drive

This is a plan for a new effect, written before any notes or DSP. When work starts, its content moves into `docs/bassforge/design-notes.md` and `docs/bassforge/circuit-notes.md`, and this page is deleted. `BassForge` is a working name, chosen to be neutral.

## 1. The aim

The goal is the modern heavy bass sound associated with parallel clean-and-drive bass preamps: a solid, undistorted fundamental under an aggressive, articulate, growling upper register that cuts through a dense mix. The best-known pedals of this kind come from one Finnish maker. Its name and product names appear in this plan only to identify the reference style, and they are in `tools/trademarks.txt` so none of them reaches the plugin.

“World class” has to mean something a test can check. This plan sets it as:

* **Low end that never collapses.** At any Drive and Blend setting, the low strings keep their weight and phase. There is no notch where the clean and driven paths meet.
* **Grit without fizz or mud.** A harmonic profile with strong low-order harmonics, controlled top end, and less two-note intermodulation than BassGrit at the same distortion.
* **Clean digital behaviour.** Aliasing well below BassGrit’s, CPU and latency inside the repo budgets, no zipper on any control.
* **Feel.** The drive cleans up when played softly and tightens rather than flubs when played hard.
* **Usable everywhere.** A post-drive EQ broad enough to fit a mix without an extra plugin, and presets that are loudness-matched.

This is a **circuit-inspired** effect. It borrows the parallel blend structure and the CMOS-inverter overdrive, and it departs from the hardware wherever a digital design can do better (section 4).

## 2. What public sources say about the reference style

Facts gathered so far. All are from retailer, distributor and news pages, so they are **reported**, not documented, until the manufacturer’s manuals are checked.

| Claim | Confidence | Source |
|---|---|---|
| The overdrive is CMOS-based | Reported | [3] |
| Controls: Drive, Blend (clean against driven), Level, plus a Grunt and an Attack switch | Reported | [4], [6] |
| Grunt sets one of three bass-boost amounts **before** the clipping stage | Reported | [6] |
| Attack shapes treble before the clipper: Cut, Flat and, on the later model, Boost | Reported | [6] |
| A four-band post EQ: ±12 dB at 100 Hz, 1 kHz, 2.8 kHz and 5 kHz | Reported | [6] |
| The extended model’s mid bands switch between 250, 500 Hz and 1 kHz, and 750 Hz, 1.5 and 3 kHz | Reported, single source | [5] |
| A later revision adds a cab simulation on the direct output | Reported | [6] |
| The reference circuit’s predecessor was published as a schematic on a forum by the maker’s founder | Reported, second-hand | [1] |
| A DIY kit inspired by the drive-only model has public build documents | Reported | [2] |

No official schematic of the current pedals is public. The plan therefore models the **circuit type** (a CMOS-inverter overdrive with pre-clip voicing, blended with clean), not a trace of one pedal.

## 3. Research still to do (phase 0)

* Find and read the founder’s predecessor schematic [1] and the DIY build documents [2]. Use them for component values and topology only, redrawn in KiCad from the text, never copied as images.
* Read the manufacturers’ own manuals to confirm the control list and EQ frequencies, and to upgrade claims from reported to documented.
* Collect public analyses of CMOS-inverter overdrives (unbuffered CD4049UB and CD4069UB used as linear amplifiers, as in well-known DIY designs) and the inverter datasheet transfer curves, for the waveshaper’s shape and its dependence on supply voltage.
* Add any newly met product names (for example `B3K`, `B7K`, `B7K Ultra`) to `tools/trademarks.txt` before they appear anywhere in `docs/`.

## 4. Departures: what the plugin can do that the pedal cannot

Each departure is a design choice with its own target in section 7.

1. **Continuous Weight and Bite.** Grunt and Attack are three-way switches on the hardware. Here they become continuous controls, named **Weight** (pre-clip low shelf) and **Bite** (pre-clip high shelf, from cut to boost), each smoothed so a full sweep makes no zipper.
2. **Clean Range morph.** The hardware blends a full-range clean signal. The plugin adds **Clean Range**, which morphs the clean path from full range (as the hardware) to only the band below a crossover (as BassGrit). It does this as `clean = LP + (1 − r)·HP` with a Linkwitz-Riley pair. The two bands are in phase, so turning the control changes only the level above the crossover, never the phase, and at 0 the clean path is an all-pass. A switched analogue filter would make a phase step at the crossover as it moved.
3. **Dynamic tightening (the original part).** A base-rate envelope of the input lowers the Weight boost on hard notes, so a dig-in tightens the low end going into the clipper instead of flubbing it, and a soft passage gets the full growl. It uses the `oversample4c` pattern from [Designing for feel](../designing-for-feel.md). Its depth is a control, **Tighten**, and 0 gives the static hardware behaviour.
4. **Phase-aligned blend.** The driven path’s pre-clip filters shift the phase of the low end. The clean path gets a matching all-pass (plus the `pk.os4Latency` delay) so the small-signal sum has no notch at any Blend.
5. **Sweepable four-band post EQ.** Low shelf, two peaking mids with swept frequency, and a high shelf. The default frequencies match the reported fixed bands, so the hardware sound is a preset, not a limit.
6. **Optional speaker voicing.** A light, minimum-phase speaker-and-cab voicing on the output, reusing BassPreamp’s Cab Bypass crossfade, so the plugin works straight into a DAW. Off by default because most players will use their own impulse response.

A compressor before the drive is out of scope for 0.1.0. It is a candidate for a later version (section 10).

## 5. Block diagram

```text
in → DC block (5 Hz) ─┬──────────────── clean path ─────────────────────┐
                      │   LR4 split at Crossover, Clean Range morph,    │
                      │   phase-match all-pass, @(latency)              │
                      │                                                 ├→ Blend → post EQ (4-band)
                      │                                                 │   → speaker voicing (opt.)
                      └→ input gain (Drive) → Weight low shelf          │   → Level → pk.safety(0.989) → out
                         ↑ (depth − Tighten · envelope)                 │
                         → Bite high shelf → 4x OS [CMOS stage 1 →      │
                           CMOS stage 2] → interstage/post low-pass ────┘
```

| Block | New or reused |
|---|---|
| DC blocker | Reused, `fi.dcblockerat(5)` |
| LR4 band split | Exists in `src/bassgrit.dsp`; move it to `pedalkit.lib` as `lr4split(f)` now that two effects need it, and update BassGrit |
| Weight and Bite shelves | Reused, `pk.lowShelf2` and `pk.highShelf2` |
| Tightening envelope | New, a base-rate peak follower; candidate for `pedalkit.lib` if it proves general |
| CMOS inverter shaper | New: `pk.cmosInv(vdd, gain)`, memoryless and asymmetric, fitted to datasheet transfer curves |
| 4x oversampling | Reused, `pk.oversample4c` (the shaper takes the envelope as its control) |
| Phase-match all-pass | New in the effect file |
| Peaking EQ | New in `pedalkit.lib` (`peak2(g, f, q)`) unless an existing effect already has one to move there |
| Speaker voicing | Reused from BassPreamp |
| Safety limiter | Reused, `pk.safety(0.989)` |

**Latency.** If the two CMOS stages need a filter between them, they need two oversamplers, at 64 samples in all. That is inside the 128-sample budget. Phase 2 tries a single composite shaper first (32 samples) and keeps the second oversampler only if the measured harmonic profile needs it. The bargraph and the dry delay come from one constant, `latencySamples`.

## 6. Draft controls

The order is fixed once released, so it is settled here. All values are **chosen** and will be retuned by ear.

| # | Label | Unit | Range | Default | Purpose |
|---|---|---|---|---|---|
| 0 | Drive | % | 0 to 100 | 50 | Gain into the CMOS stages |
| 1 | Blend | % | 0 to 100 | 50 | 0 is clean only, 100 is driven only |
| 2 | Level | dB | −40 to +12 | 0 | Output level |
| 3 | Weight | dB | 0 to +15 | +6 | Pre-clip low shelf (around 120 Hz, inferred from the reported bass-boost function) |
| 4 | Bite | dB | −12 to +12 | 0 | Pre-clip high shelf (around 2 kHz, chosen) |
| 5 | Tighten | % | 0 to 100 | 30 | How much hard playing reduces Weight |
| 6 | Clean Range | % | 0 to 100 | 0 | 0 is full-range clean, 100 is clean below the crossover only |
| 7 | Crossover | Hz | 40 to 400 | 150 | Split frequency for Clean Range |
| 8 | Bass | dB | −12 to +12 | 0 | Post low shelf at 100 Hz |
| 9 | Low Mid | dB | −12 to +12 | 0 | Post peak, swept by control 10 |
| 10 | Low Mid Freq | Hz | 200 to 1200 | 500 | |
| 11 | High Mid | dB | −12 to +12 | 0 | Post peak, swept by control 12 |
| 12 | High Mid Freq | Hz | 700 to 4000 | 1500 | |
| 13 | Treble | dB | −12 to +12 | 0 | Post high shelf at 5 kHz |
| 14 | Speaker | % | 0 to 100 | 0 | Crossfade into the speaker voicing |

Fifteen controls is a lot. Phase 1 should ask whether the swept-frequency controls belong in 0.1.0, or whether fixed bands are enough at first. Controls can be appended later, but not removed or reordered after release.

## 7. Measurable targets

These become `tests/bassforge/test_targets.py` and `test_dynamics.py`, alongside the minimum set and `tests/common/`. The numbers are first guesses and **chosen**. Where possible, a target is set relative to BassGrit or BassDrive so the claim “better” is measured, not asserted.

1. **Phase-coherent blend.** At small signal (−40 dBFS, where the shaper is near linear) the output response from 30 Hz to 8 kHz, at Blend 0, 50 and 100, has no dip deeper than 1 dB relative to the smooth average.
2. **Clean Range keeps its phase.** With Blend 0 and Clean Range 0, the response is flat within 0.3 dB from 30 Hz to 8 kHz. At Clean Range 100, the response follows the analytic LR4 low-pass within 0.5 dB, and at every setting the phase matches the LR4 all-pass within 5°.
3. **The fundamental survives.** At Blend 50 and Drive 100, a 41 Hz and a 31 Hz tone at −12 dBFS keep their fundamental within 3 dB of the Drive 0 level.
4. **Harmonic profile.** At Drive 50, H2 is within 10 dB of H3 (the CMOS asymmetry gives even-order content), and the harmonics above H9 fall by at least 12 dB per octave.
5. **Intermodulation.** A two-note test (41.2 Hz plus 61.7 Hz, a fifth on the low strings) at matched upper-band THD gives at least 6 dB less low-frequency IMD than BassGrit.
6. **Weight and Bite act before the clipper.** Weight +12 dB raises the low-band harmonic content (measured on a 60 Hz tone) by at least 6 dB more than the same boost in the post EQ would, which shows it drives the clipper, not just the output.
7. **Tighten works.** On `pluck` at −6 dBFS against −30 dBFS, with Tighten 100, the low-band level reaching the shaper is at least 6 dB lower, relative to the input, on the hard note. With Tighten 0 the difference is under 1 dB.
8. **Cleanup curve.** `harmonic_trajectory` from −40 to 0 dBFS input at Drive 50 is monotonic, and THD passes 1 % between −30 and −18 dBFS.
9. **Aliasing.** At Drive 100, the worst alias for a 1.1 kHz tone is below −60 dBc with 4x oversampling, against BassGrit’s −45.8 dBc. The softer CMOS curve should make this possible. If it doesn’t, the notes say so.
10. **Loudness.** Every preset is within 1 LU of the others.

## 8. Work plan

Each phase ends with a commit to this PR. The PR stays a draft until phase 7 passes.

* **Phase 0: research.** Section 3. Output: a source list, trademark additions, and a go or no-go on the founder’s schematic as a value source.
* **Phase 1: notes.** `docs/bassforge/design-notes.md` (idea, departures, targets, feel) and `docs/bassforge/circuit-notes.md` (the CMOS stage and pre-clip voicing, with values and corner frequencies). Every constant gets a confidence level. This plan page is then deleted.
* **Phase 2: library.** Add `cmosInv`, `lr4split` and `peak2` to `src/lib/pedalkit.lib`, documented in `AGENTS.md` and `docs/development/pedalkit-lib.md`. Move BassGrit onto `lr4split` and rerun `make test` across all effects to show it is unchanged.
* **Phase 3: DSP.** `src/bassforge.dsp`, following section 5, at version 0.1.0 with `lv2class "DistortionPlugin"`.
* **Phase 4: tests.** The minimum set (`test_silence`, `test_peak`, `test_freqresp`, `test_harmonics`, the `RENDER_1X` aliasing comparison) plus `test_targets`, `test_dynamics` and `test_presets`. Plots as SVG, numbers as CSV.
* **Phase 5: presets.** `src/bassforge.presets.toml`, with every control set: a hardware-style setting (fixed bands, full-range clean), a modern metal setting, a fingerstyle grit setting and a tight five-string setting.
* **Phase 6: docs and schematic.** `docs/bassforge/index.md` with the download marker, the changelog with `## [0.1.0]`, rows in the README, `docs/index.md` and `docs/effects/index.md`, the `mkdocs.yml` nav, and `tools/schematics/bassforge.py` for the modelled CMOS stage.
* **Phase 7: checks.** `make lv2 lint test`, `make vst3 pluginval`, `make clap clap-validate`, `make test web schematics docs` and `make check`, all with `FX=bassforge`. Read every plot. Then mark the PR ready for review.

## 9. What only listening can decide

* The Weight and Bite corner frequencies, and whether Bite boost sounds articulate or harsh.
* Tighten’s attack and release times. They start at about 5 ms and 150 ms (chosen) and decide whether the effect feels responsive or pumps.
* Whether one CMOS stage or two gives the right growl.
* The default Crossover for Clean Range, especially on a five-string low B (31 Hz).
* Whether the speaker voicing helps or should go.

## 10. Risks and later work

* **Sourcing.** If the founder’s schematic cannot be found or used, the CMOS stage is designed from the datasheet and general analyses, and the effect is described as original rather than circuit-inspired.
* **Control count.** If fifteen controls feel too many, the swept mid frequencies move to version 0.2.0.
* **Later:** an optical-style compressor before the drive, a noise gate, and an envelope-follower mode where Blend itself follows playing strength.

## Sources

1. Fractal Audio forum, “Fractal Audio drive models: Blackglass 7K, based on …”, a user’s report of the predecessor schematic. <https://forum.fractalaudio.com/threads/fractal-audio-drive-models-blackglass-7k-based-on-darkglass-microtubes-b7k.132521/>
2. PCBGuitarMania, *Black Mirror* build documents (a DIY kit inspired by the drive-only model). <https://pcbguitarmania.com/wp-content/uploads/2018/06/Black-Mirror-Building-Docs.pdf>
3. Shimamura (Japanese distributor), product article describing the drive-only model as CMOS-based. <https://www.shimamura.co.jp/update/?p=3600>
4. Kirstein, retailer listing for the drive-only model. <https://www.kirstein.de/Spezielle-Basseffekte/Darkglass-Microtubes-B3K.html>
5. No Treble, announcement of the extended model, with its switchable mid frequencies. <https://www.notreble.com/?p=41909>
6. Guitar Center, retailer listing for the extended model (controls and EQ bands). <https://www.guitarcenter.com/Darkglass/Microtubes-B7K-Ultra-V2-Bass-Preamp-Pedal-Aux-In-1500000317420.gc>
