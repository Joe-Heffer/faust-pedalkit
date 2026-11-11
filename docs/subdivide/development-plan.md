# Development plan: SubDivide

This is a working plan for a new effect, kept with the code while it is in progress. It is not in the site's `nav`; fold what remains useful into `design-notes.md` and delete this page before the first release.

## Context

The request was for a clean-room octave-down pedal in the spirit of a well-known compact digital octave pedal (named in `tools/trademarks.txt`), whose Vintage mode reproduces its analogue predecessor. Agreed scope:

* A monophonic flip-flop divider core with departures the hardware can't make. No polyphonic mode.
* Voiced and tested for guitar and bass: low B (30.9 Hz) to about 1 kHz fundamentals.

Neutral name `subdivide`, `declare name "SubDivide"`, URI `urn:pedalkit/subdivide`, `lv2class "PitchPlugin"`, version `0.1.0`.

## Change from the first plan: original, not circuit-inspired

The first plan treated the effect as circuit-inspired, with circuit notes and a KiCad schematic of the analogue predecessor's divider. The cloud session that drafted this could not reach the reference pages (the manual PDF and the forum and wiki analyses of the schematic were outside its network allowance), so no component value could be sourced. AGENTS.md rule 4 forbids guessing values, so the effect is now **original**:

* `docs/subdivide/design-notes.md` only. No circuit notes, and so no schematic script.
* The reference pedals appear under *Prior art* as inspiration, for behaviour that public sources describe (below), never for values.
* If the schematic analyses can be read later, circuit notes can still be added, and the effect reclassified as circuit-inspired.

What the sources that could be read say (search-result quotations only; confirm before citing):

1. Product listings and a third-party manual summary for the digital pedal: controls are Direct Level, −1 Oct, +1 Oct and a −2 Oct/Range knob, with a Vintage/Poly switch and a rear Guitar/Bass switch. In Vintage, the Range knob sets the −2 octave level; in Poly it sets the lowest note that gets the octave. Links: [manuals.plus summary](https://manuals.plus/asin/B08JGC9LLP), [Full Compass listing](https://fullcompass.com/prod/595287-boss-oc-5-octave-pedal-with-vintage-and-polyphonic-modes).
2. Forum notes on the analogue predecessor: the first half of a CD4013 dual flip-flop divides by two and the second half divides again for −2; two comparators of half-wave rectified signals against the low-passed signal drive the first flip-flop's set and reset; tracking needs the fundamental to stay above a threshold. Link: [diystompboxes thread](https://diystompboxes.com/smfforum/index.php?msg=456533).
3. A general description of the polarity-inverting divider (a zero-crossing detector drives a flip-flop that inverts every other cycle, which keeps the input's waveform), in a software module's manual: [Audio Octave Divider](https://www.brainmodular.com/manuals/hh7/en/modules/audio/fx/audio-octave-divider). No source found says the analogue predecessor works this way, so the notes must not claim it.

## The design

Core principle (prior art): low-pass the input to isolate the fundamental, detect its cycles, toggle a flip-flop on each cycle (÷2) and a second one on each rising toggle of the first (÷4).

Departures, each to become a measurable target in the design notes:

1. **Zero-crossing switching with a level-relative arm.** A divider fires only at an upward zero crossing of the detector signal after a dip below −`hyst` × envelope. The edge is placed between samples (on the switching sample the output is the interval's average). The polarity flips where the signal is near zero, so the inverted-cycle sub has a corner rather than a step. This is meant to keep aliasing low **without oversampling**, so no latency and no Latency bargraph.
2. **Shape control.** Crossfades between the classic divided square (envelope × flip-flop) and the input with every other cycle (or pair of cycles) inverted (detector × flip-flop), which keeps the player's waveform.
3. **Pitch-tracking low-pass on each sub.** The period between fires gives a pitch estimate, which is clamped and glided. Each sub gets a 4th-order Butterworth low-pass (two `fi.svf.lp` sections) at `Tone` × its own frequency, so the sub is equally round across the neck. The filter also suppresses the 3f/2 (÷2) and 3f/4, 5f/4 (÷4) products that polarity switching creates.
4. **Gate with hysteresis** (open above `Gate`, close 6 dB below, 10 ms fade). Decaying tails and noise can't produce mistracked garbage.
5. **Range.** It sets the detector's low-pass corner and the fastest allowed fire rate, and fades the subs out over half an octave above that note instead of letting them glitch.

### Controls (`[n]` order fixed from the start)

| # | Label | Unit | Range / default | Purpose |
|---|---|---|---|---|
| 0 | Direct | dB | −60…+6 / 0 | Dry level. A dB floor rather than off, so `tests/common/test_latency.py` "all minimum" still measures an impulse response |
| 1 | Sub 1 | % | 0…100 / 70 | −1 octave level |
| 2 | Sub 2 | % | 0…100 / 0 | −2 octave level |
| 3 | Range | Hz | 200…1500 / 700 | Highest tracked note |
| 4 | Tone | % | 0…100 / 50 | Tracking low-pass, 1× to 4× the sub's frequency (log) |
| 5 | Shape | % | 0…100 / 50 | Divided square to inverted-cycle input |
| 6 | Gate | dB | −80…−20 / −55 | Sub gate threshold |
| 7 | Level | dB | −24…+12 / 0 | Output |

### Constants

All chosen except the Butterworth Qs (documented), with their intent commented at the top of `src/subdivide.dsp`: `detHpF` 20 Hz, `detLpN` 4, `envAtt` 1 ms, `envRel` 50 ms, `hyst` 0.25, `maxRateMul` 2, `pitchTau` 5 ms, `pitchLo` 25 Hz, `toneLoMul`/`toneHiMul` 1 and 4, `fadeOct` 0.5, `gateHyst` 6 dB, `gateTau` 10 ms, `sqTrim`/`flTrim`/`sub1Trim`/`sub2Trim` (placeholders until measured). An open question for the notes: −2 octaves on low B lands near 7.7 Hz, which only the 5 Hz DC blocker touches.

## Status of this branch

* `src/subdivide.dsp`: a first draft. It compiles with the pinned faustwasm (Faust 2.90.17), but **the subs are silent**: a smoke render at 41, 110, 330 and 660 Hz gave only the −60 dB direct path. The dividers never fire, so the `dividers` letrec (the arm/fire logic, or the `s1 == 0` initialisation) is the first thing to debug. Nothing else has been measured.
* `tools/trademarks.txt`: the reference pedals' model names added.
* Everything else below is still to do. Until it is done, the `effect-checklist` hook and CI fail on this branch.

## Remaining work

1. **Fix the dividers**, then measure and set the trims.
2. **Design notes**: write `docs/subdivide/design-notes.md` (outline in `docs/development/designing-new-sounds.md`) with the idea, the prior art above, blocks, constants table, measurable targets, dynamics and feel, and open questions.
3. **Tests** in `tests/subdivide/`, following `tests/midhump/`:
   * `test_silence.py`
   * `test_peak.py`
   * `test_freqresp.py`: the direct path is flat; sub level against input note.
   * `test_harmonics.py`: spectra on sines at 41, 110, 330 and 660 Hz.
   * `test_targets.py`:
     * output fundamental at f/2 and f/4 within 1 %
     * sub level within ±3 dB across notes
     * f/2 at least 12 dB over 3f/2 at Tone 50
     * energy off the f/4 grid (aliases) below −60 dBc up to 660 Hz
     * subs silent half an octave above Range
     * subs silent below the gate
   * `test_dynamics.py` (`pluck`, `burst`, `harmonics_over_time`):
     * sub onset within two input periods
     * the gate closes cleanly on the tail
     * no extra toggles as a note decays
     * a two-note plot that documents the monophonic limitation
   * `test_presets.py`
   * There is no `RENDER_1X` comparison, because the effect doesn't oversample. If the alias target fails, try a better sub-sample edge before reaching for `pk.oversample4c`.
4. **Presets**: `src/subdivide.presets.toml`, for example "Vintage sub", "Two octaves down", "Bass floor" and "Guitar bass-line", with every control set.
5. **Docs**:
   * `docs/subdivide/index.md` (with `<!-- downloads:subdivide -->`) and `changelog.md` (`## [0.1.0]`)
   * rows in `README.md`, `docs/index.md` and `docs/effects/index.md`
   * `mkdocs.yml` nav
6. **Library**: if the zero-crossing divider and the period pitch tracker come out general, move them to `src/lib/pedalkit.lib` and document them in `AGENTS.md` and `docs/development/pedalkit-lib.md`.
7. **Verify**:
   * `make lv2 lint test FX=subdivide`, including `tests/common/`. Watch `test_latency.py` "all minimum" (Direct −60 dB), `test_zipper.py` on Range and Tone (modulated filter corners) and `test_cpu.py` (per-sample `tan` in four SVF sections).
   * `make vst3 pluginval FX=subdivide`
   * `make clap clap-validate FX=subdivide`
   * `make test web docs`
   * `make check`
   * Read every plot in `tests/out/subdivide/`.

## Tuning by ear, once it works

* `Tone` and the tracking filter order: how round or buzzy the sub is.
* `hyst`: tracking robustness on bass with a strong second harmonic.
* `envRel` and the gate timing: behaviour on decaying notes.
* The sub trims, and Shape's default.
* Chords and notes below low E, which are expected to mistrack, as on any monophonic divider.
