# Design notes: MidHump

MidHump is a **circuit-inspired** effect. The borrowed part is the mid-hump overdrive described in the [circuit notes](circuit-notes.md). The departure is a full-range clean blend and a few choices a pedal would not make.

## 1. The idea

The reference circuit amplifies mids and leaves bass at unity gain. That keeps the low end tight, but the clipped signal then has almost no energy below about 500 Hz, and the 723 Hz low-pass removes most of what is left above it. The pedal sounds focused and slightly thin on a bass, and on a guitar it pushes an amplifier's input stage.

What a player gets that the pedal does not give: **Blend** adds a clean, full-range copy of the input in parallel. The mid hump stays, and the lowest octave and the top end that the 723 Hz filter removes come back, without turning Drive down.

Measurable description:

- Small-signal response peaks between 500 Hz and 1.5 kHz at high Drive, with 100 Hz at least 8 dB below the peak.
- Distortion is odd-order (even/odd ratio below −30 dB at Drive 100).
- Output keeps rising with input level after the diodes conduct.
- At playing level, Blend 100 % lifts 30 Hz to 60 Hz by about 3 dB and leaves the clipped mids dominant.

## 2. Prior art

1. The reference circuit and its analyses: see [circuit notes](circuit-notes.md), sources 1 to 6.
2. Clean-blend overdrives (a parallel clean path to keep the low end) are common on bass pedals. [BassDrive](../bassdrive/index.md) uses a crossfade. MidHump adds the clean path rather than crossfading, so Blend 0 is exactly the circuit.

## 3. Blocks

| Block | New or reused |
|---|---|
| Input high-pass, 723 Hz low-pass, DC blocker | Reused (`fi` library) |
| 4x oversampling around a memoryless clipper | Reused (`pk.oversample4`) |
| Diode pair | Reused (`pk.softSat`) |
| Frequency-dependent clip stage, the sum of input and limited branch | New in this file |
| Tone shelf | Reused (`pk.tf1a`) |
| Clean blend, delayed by `pk.os4Latency` | New in this file, same pattern as BassDrive |
| Output safety limiter | Reused (`pk.safety`) |

Nothing here is general enough to move into `pedalkit.lib` yet. If a second effect needs the "input plus limited branch" structure, it should be moved there.

## 4. Constants

All circuit values and their confidence are in section 9 of the circuit notes. The constants that belong to this design alone:

| Constant | Value | Confidence | Intent |
|---|---|---|---|
| `cleanTrim` | 0.5 | Chosen | Blend 100 % adds the clean path at half amplitude. It lifts 30 Hz to 60 Hz by 2.6 dB to 3.1 dB at −20 dBFS input (measured), without burying the mids. Retune by ear. |
| Blend range | 0 to 100 %, default 0 | Chosen | Default 0 gives the reference circuit. |
| Blend law | additive | Chosen | A crossfade would remove the drive as Blend rises. |

## 5. Measurable targets

These are checked in `tests/midhump/test_targets.py`, `test_freqresp.py` and `test_harmonics.py`. The measured values are from the first build (October 2026).

1. The small-signal response is within 0.5 dB of the analytic model from 50 Hz to 4 kHz at Drive 0, 50 and 100. Measured: within 0.16 dB.
2. The response peaks at 500 Hz to 1.5 kHz at Drive 100, Tone 50 and 100 Hz is at least 8 dB below the peak. Measured: peak at 826 Hz, 100 Hz 12.1 dB below it.
3. Gain at 2 kHz runs from about 21 dB at Drive 0 to about 41 dB at Drive 100. Measured: 20.9 dB to 40.4 dB.
4. The even/odd harmonic ratio is below −30 dB at Drive 100. Measured: no even harmonics above the float noise floor (−177 dB or lower).
5. The 1 kHz fundamental still rises with input level in the top 18 dB of the range.
6. Blend adds exactly `cleanTrim` times the input, time-aligned with the driven path: Blend 100 minus Blend 0 is within 0.3 dB and 2° of 0.5 × the input high-pass from 100 Hz to 10 kHz. Measured: 0.02 dB and 0.19°.
7. At −20 dBFS input, Blend 100 % lifts 30 Hz to 60 Hz by 2 dB to 4.5 dB at Drive 0, 50 and 100. Measured: 3.1, 3.1 and 2.6 dB.

   The first draft expected about 3.5 dB (20 · log10 1.5) at any level, assuming the driven path is at unity gain below 100 Hz. It is not: the branch term (Rf/R4) · f/720 Hz is 90° out of phase with the input and, unclipped, is already 1.3 times the input at 45 Hz at Drive 50 and 7.3 times at Drive 100. So at small signals the clean half adds to a larger, partly quadrature sum, and the lift falls from 2.6 dB at Drive 0 to 0.1 dB at Drive 100. At playing level the branch clips and the lift comes back to about 3 dB.
8. 4x oversampling lowers the worst alias by at least 20 dB against a 1x build, and the worst alias for a 1.1 kHz tone is below −60 dBc. Measured: 24.5 dB lower at 3.7 kHz and 46.0 dB lower at 1.1 kHz, where the worst alias is −83.3 dBc.

## 6. Open questions

Only listening can answer these.

- Is `cleanTrim` 0.5 the right amount? Does Blend near 100 % sound hollow because of the phase difference between the clean and driven paths? Measurement shows the clean path is time-aligned, but the driven path itself is up to 90° from the input in the bass (target 7 above), so the two add in partial quadrature there.
- Does the soft 0.6 V knee (`Vd`) sound like the pedal at low Drive?
- Does the log Drive law put the useful range where a player expects it?
- Does the behavioural Tone shelf feel as wide as the pedal's?
