# Design notes: MidHump

MidHump is a **circuit-inspired** effect. The borrowed part is the mid-hump overdrive described in the [circuit notes](circuit-notes.md). The departure is a full-range clean blend and a few choices a pedal would not make.

## 1. The idea

The reference circuit amplifies mids and leaves bass at unity gain. That keeps the low end tight, but the clipped signal then has almost no energy below about 500 Hz, and the 723 Hz low-pass removes most of what is left above it. The pedal sounds focused and slightly thin on a bass, and on a guitar it pushes an amplifier's input stage.

What a player gets that the pedal does not give: **Blend** adds a clean, full-range copy of the input in parallel. The mid hump stays, and the lowest octave and the top end that the 723 Hz filter removes come back, without turning Drive down.

Measurable description:

* Small-signal response peaks between 500 Hz and 1.5 kHz at high Drive, with 100 Hz at least 8 dB below the peak.
* Distortion is odd-order (even/odd ratio below −30 dB at Drive 100).
* Output keeps rising with input level after the diodes conduct.
* Blend 100 % lifts 30 Hz to 60 Hz by about 3.5 dB and leaves the clipped mids dominant.

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
| `cleanTrim` | 0.5 | Chosen | Blend 100 % adds the clean path at half amplitude. It lifts the low end by about 3.5 dB without burying the mids. Retune by ear. |
| Blend range | 0 to 100 %, default 0 | Chosen | Default 0 gives the reference circuit. |
| Blend law | additive | Chosen | A crossfade would remove the drive as Blend rises. |

## 5. Measurable targets

These are checked in `tests/midhump/test_targets.py` and `test_harmonics.py`.

1. The small-signal response is within 1.5 dB of the analytic model from 50 Hz to 4 kHz at Drive 0, 50 and 100.
2. The response peaks at 500 Hz to 1.5 kHz at Drive 100, Tone 50 and 100 Hz is at least 8 dB below the peak.
3. Gain at 2 kHz runs from about 21 dB at Drive 0 to about 41 dB at Drive 100.
4. The even/odd harmonic ratio is below −30 dB at Drive 100.
5. The 1 kHz fundamental still rises with input level in the top 18 dB of the range.
6. Blend 100 % lifts 30 Hz to 60 Hz by 2.5 dB to 4.5 dB.
7. 4x oversampling lowers the worst alias by at least 20 dB against a 1x build, and the worst alias for a 1.1 kHz tone is below −60 dBc.

## 6. Open questions

Only listening can answer these.

* Is `cleanTrim` 0.5 the right amount? Does Blend near 100 % sound hollow because of the phase difference between the clean and driven paths?
* Does the soft 0.6 V knee (`Vd`) sound like the pedal at low Drive?
* Does the log Drive law put the useful range where a player expects it?
* Does the behavioural Tone shelf feel as wide as the pedal's?
