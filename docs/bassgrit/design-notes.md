# Design notes: BassGrit

BassGrit is a **circuit-inspired** effect. The borrowed part is the op-amp hard-clipping distortion described in the [circuit notes](circuit-notes.md): a gain stage whose gain-bandwidth limit darkens it as the gain rises, a diode pair clipping to ground, and a passive low-pass. The departures are a band split that keeps the low end out of the clipper, a Filter range moved down, and a Low Blend control.

## 1. The idea

On a bass, a hard-clipping pedal has two problems. Everything below the grounded legs' corners (60 Hz, 1.5 kHz) is amplified only by 1, but from 60 Hz up the stage has the full gain, so a note's fundamental is clipped along with its harmonics. Clipping a 41 Hz to 98 Hz fundamental to a square wave also makes intermodulation with the other strings, and the result is mud rather than grit.

What a player gets that the pedal does not give: the signal is **split at a Crossover** (default 120 Hz) with a 4th-order Linkwitz-Riley filter. Only the upper band goes into the gain stage and the diodes. The lower band bypasses them and comes back at **Low Blend**. The fundamental stays clean and tight, and the upper harmonics of the note, the string noise and the picking get the full hard-clipped, bandwidth-limited treatment.

Measurable description:

- With Distortion 0, Filter 0 and Low Blend 100, the response is flat (the two bands sum to an all-pass).
- A 41 Hz fundamental passes within 3 dB of its Distortion 0 level at Distortion 50, while 1 kHz rises by more than 25 dB.
- A 41 Hz tone at −12 dBFS has at least 20 dB less harmonic distortion with the split (Crossover 120 Hz) than with the lowest Crossover (40 Hz).
- The distortion is odd-order (symmetric clipping).
- Small-signal bandwidth falls as Distortion rises (the gain-bandwidth pole).

## 2. Prior art

1. The reference circuit and its analyses: see [circuit notes](circuit-notes.md), sources 1 to 5.
2. Split-band distortion for bass (a clean low band blended with a driven upper band) is common on bass pedals. [BassDrive](../bassdrive/index.md) and [MidHump](../midhump/index.md) both blend a clean path. BassGrit differs in that the clean path is the **low band only**, so the low band and the driven band do not overlap, and the sum is an all-pass.

## 3. Blocks

| Block | New or reused |
|---|---|
| DC blocker (5 Hz) | Reused (`fi.dcblockerat`) |
| Linkwitz-Riley 4th-order band split | New in this file (two Butterworth sections per side from `fi.lowpass`/`fi.highpass`) |
| Gain stage: input plus the scaled-high-pass branch with feedback and gain-bandwidth poles | New in this file; the structure is MidHump's "input plus branch" |
| Hard diode pair | Reused (`pk.kneeClip`) inside `pk.oversample4` |
| Filter low-pass | Reused (`fi.lowpass`) |
| Clean low band, delayed by `pk.os4Latency` | Same pattern as BassDrive and MidHump |
| Output safety limiter | Reused (`pk.safety`) |

The band split has no circuit behind it, so the schematic draws a standard analogue stand-in (sheet 8: four unity-gain Sallen-Key sections, all chosen):

![Sheet 8: the band split](../schematics/bassgrit/bassgrit-8-band-split.svg)

Nothing here is general enough to move into `pedalkit.lib` yet. MidHump and BassGrit now both use the "input plus branch" structure, so a shared `opampBranch` helper is a candidate if a third effect needs it.

## 4. Constants

The circuit values and their confidence are in the [circuit notes](circuit-notes.md), sections 3 to 6. The constants that belong to this design alone:

| Constant | Value | Confidence | Intent |
|---|---|---|---|
| Crossover range | 40 to 400 Hz, default 120 Hz | Chosen | Default above the open strings of a four-string bass (41 to 98 Hz) and below the usual start of the mids. Retune by ear. |
| Crossover slope | 4th-order Linkwitz-Riley | Chosen | The two bands are in phase and sum flat, and 24 dB/octave keeps the fundamental out of a gain stage that has 45 dB of gain from 60 Hz up. 2nd order left a 41 Hz fundamental 25 dB higher in the clipper at full Distortion (measured). |
| Low Blend | 0 to 100 %, default 70 | Chosen | 100 % makes the unclipped response flat. The default leaves some room for the driven band. |
| `Cfilt` | 4.7 nF | Chosen | The pedal's 3.3 nF gives 475 Hz to 32 kHz. 4.7 nF gives 334 Hz to 22.6 kHz, which keeps the darkest setting usable on bass. |
| Filter law | log taper | Chosen | Same as the pedal's audio-taper pot and the other effects' pots. |
| `Vd`, `nKnee` | 0.6 V, 4 | Chosen | Silicon diode threshold; the knee is harder than tanh. See circuit notes section 5. |
| `GBW` | 1 MHz | Inferred | Order of magnitude only. |
| `outTrim` | 1.2 | Chosen | Restores a little of the level lost to the 0.6 V clip. It is applied to both bands, so Distortion 0 is flat. |
| Level range | −40 to +12 dB | Chosen | As in the other effects. |

## 5. Measurable targets

These are checked in `tests/bassgrit/test_targets.py`, `test_freqresp.py` and `test_harmonics.py`. The measured values are from the first build (October 2026).

1. With Distortion 0, Filter 0 and Low Blend 100, the response is flat within 1 dB of `outTrim` from 30 Hz to 8 kHz. Measured: within 0.21 dB. This also shows the clean band is time-aligned with the driven band.
2. The 41 Hz gain at Distortion 50 is within 3 dB of Distortion 0, and the 1 kHz gain rises by more than 25 dB. Measured: +0.7 dB and +41.1 dB.
3. 41 Hz at −12 dBFS, Distortion 50: THD at least 20 dB lower at Crossover 120 Hz than at 40 Hz. Measured: −77.2 dB against −11.6 dB.
4. The 1 kHz small-signal gain runs from under 3 dB at Distortion 0 to over 45 dB at Distortion 100. Measured: 1.6 dB to 55.6 dB.
5. The gain-bandwidth pole: 5 kHz is at least 6 dB below 1 kHz at Distortion 100, and at least 3 dB further down than at Distortion 50. Measured: −8.9 dB at Distortion 100 and +1.7 dB at Distortion 50.
6. The Filter 100 over Filter 0 response follows the analytic one-pole ratio within 0.7 dB from 100 Hz to 5 kHz. Measured: 0.51 dB, with the corner at 334 Hz.
7. Low Blend 100 lifts 30 Hz to 60 Hz by at least 6 dB at Distortion 50 and −20 dBFS. Measured: +11.6 dB. At Distortion 100 the lift is only +3.4 dB (reported, not a target): the clipper's 45 dB of gain from 60 Hz still catches the lower skirt of the upper band, so at full Distortion the low band is less clean than at moderate settings.
8. At Distortion 25, 10 dB input steps rise at 1 kHz, and the last rises by under 6 dB (compression). Measured: +9.9, +7.3 and +1.3 dB.
9. Even/odd harmonic ratio below −30 dB at Distortion 100. Measured: −81.7 dB at 110 Hz and −89.8 dB at 220 Hz.
10. 4x oversampling lowers the worst alias by at least 20 dB at 221 Hz and 441 Hz, and the worst alias at 441 Hz is below −60 dBc. Measured: 42.5 dB and 24.0 dB, and −61.5 dBc. At 1.1 kHz the worst alias with 4x is −45.8 dBc (16.5 dB better than 1x), and at 3.7 kHz −34.5 dBc. A near-square wave has harmonics that fall only as 1/k, and 4x oversampling cannot remove aliasing from that, so the effect is not alias-clean above about 500 Hz at full Distortion.

## 6. Open questions

Only listening can answer these.

- Is 120 Hz the right default Crossover? Does a five-string low B (31 Hz) need a lower one?
- Does the effect at full Distortion sound too thin, because the low band is only 70 % at default and the driven band has almost no energy below 100 Hz?
- Is the bass Filter range (334 Hz to 22.6 kHz) right, or should the darkest setting be higher?
- Does the 4th-order split cause audible phase smear on the attack of a note near the crossover?
- Does the hard `nKnee` of 4 sound better than a softer knee?
- Would the aliasing at 1 kHz and above at full Distortion be audible on bass? (It is −45.8 dBc for a 1.1 kHz tone, and a bass seldom plays one that high with this much gain.)
