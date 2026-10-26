# Design notes: MidHump

MidHump is a **circuit-inspired** effect. The borrowed part is the mid-hump overdrive described in the [circuit notes](circuit-notes.md). The departures are a full-range clean blend, a bias shift on the diodes (Bloom) and a few choices a pedal would not make.

## 1. The idea

The reference circuit amplifies mids and leaves bass at unity gain. That keeps the low end tight, but the clipped signal then has almost no energy below about 500 Hz, and the 723 Hz low-pass removes most of what is left above it. The pedal sounds focused and slightly thin on a bass, and on a guitar it pushes an amplifier's input stage.

What a player gets that the pedal does not give: **Blend** adds a clean, full-range copy of the input in parallel. The mid hump stays, and the lowest octave and the top end that the 723 Hz filter removes come back, without turning Drive down.

**Bloom** is the second departure, and the first effect to use the bias-shift blocks in the [shared library](../development/pedalkit-lib.md#dynamic-state). The pedal's diodes sit in the op-amp's feedback path, where nothing can bias them, so the clipping is symmetric and the same on every cycle of a note. Bloom gives them a bias that charges up on loud peaks and drains away afterwards, as a coupling capacitor in front of a conducting stage would. A hard pick starts symmetric, then grows a second harmonic over the next few tens of milliseconds, and the asymmetry outlasts the loud passage. Soft playing is untouched. The aim is a drive that responds to how hard and how long the player digs in, not only to how loud the signal is at that moment.

Measurable description:

- Small-signal response peaks between 500 Hz and 1.5 kHz at high Drive, with 100 Hz at least 8 dB below the peak.
- Distortion is odd-order (even/odd ratio below −30 dB at Drive 100).
- Output keeps rising with input level after the diodes conduct.
- At playing level, Blend 100 % lifts 30 Hz to 60 Hz by about 3 dB and leaves the clipped mids dominant.
- With Bloom up, a loud tone gains a strong second harmonic that takes tens of milliseconds to build up and dies away within about a second after the tone gets quiet. Below the diode knee, Bloom changes nothing.

## 2. Prior art

1. The reference circuit and its analyses: see [circuit notes](circuit-notes.md), sources 1 to 6.
2. Clean-blend overdrives (a parallel clean path to keep the low end) are common on bass pedals. [BassDrive](../bassdrive/index.md) uses a crossfade. MidHump adds the clean path rather than crossfading, so Blend 0 is exactly the circuit.
3. Bias shift in valve stages, where grid current on loud peaks charges the coupling capacitor and moves the operating point, is described in M. Blencowe, [*Designing Tube Preamps for Guitar and Bass*](https://valvewizard.co.uk/Book1.html) (2nd edition, 2012), in its discussion of blocking distortion. Bloom borrows the mechanism (charge on peaks, slow discharge, a shift that changes the symmetry of the clipping), not any circuit's values.
4. J. Pakarinen and D. T. Yeh, “A review of digital techniques for modeling vacuum-tube guitar amplifiers”, *Computer Music Journal* 33(2), pp. 85–100, 2009 ([record](https://research.aalto.fi/en/publications/a-review-on-digital-techniques-for-modeling-vacuum-tube-guitar-am/)), discusses why static waveshapers miss this kind of level-dependent, time-varying behaviour.

## 3. Blocks

| Block | New or reused |
|---|---|
| Input high-pass, 723 Hz low-pass, DC blocker | Reused (`fi` library) |
| 4x oversampling around a memoryless clipper | Reused (`pk.oversample4`) |
| Diode pair | Reused (`pk.softSat`) |
| Frequency-dependent clip stage, the sum of input and limited branch | New in this file |
| Tone shelf | Reused (`pk.tf1a`) |
| Clean blend, delayed by `pk.os4Latency` | New in this file, same pattern as BassDrive |
| Bias shift envelope and the biased diode pair | New, in `pedalkit.lib` (`pk.biasShift`, `pk.biased`) |
| 4x oversampling with a base-rate control input | New, in `pedalkit.lib` (`pk.oversample4c`) |
| Output safety limiter | Reused (`pk.safety`) |

Nothing here is general enough to move into `pedalkit.lib` yet. If a second effect needs the "input plus limited branch" structure, it should be moved there.

## 4. Constants

All circuit values and their confidence are in section 9 of the circuit notes. The constants that belong to this design alone:

| Constant | Value | Confidence | Intent |
|---|---|---|---|
| `cleanTrim` | 0.5 | Chosen | Blend 100 % adds the clean path at half amplitude. It lifts 30 Hz to 60 Hz by 2.6 dB to 3.1 dB at −20 dBFS input (measured), without burying the mids. Retune by ear. |
| Blend range | 0 to 100 %, default 0 | Chosen | Default 0 gives the reference circuit. |
| Blend law | additive | Chosen | A crossfade would remove the drive as Blend rises. |
| Bloom range | 0 to 100 %, default 0 | Chosen | Default 0 gives the reference circuit, and the presets keep it at 0. Bloom scales the bias shift linearly. |
| `bloomThr` | `Vd` (0.6 V) | Chosen | The shift starts where the diodes start to conduct, so anything quieter than the knee is untouched (target 9). |
| `bloomMax` | 0.5 × `Vd` (0.3 V) | Chosen | The largest offset, reached on sustained hard playing at Bloom 100. It moves the knees to −0.3 V and +0.9 V, which gives H2 around −20 dBc on a loud tone at Drive 50 (measured, target 10). Larger values push H2 higher but also start to gate the quieter half-wave. |
| `bloomAtt` | 15 ms | Chosen | The charging time constant. The first cycle or two of a pick at guitar pitches stays symmetric, and the second harmonic blooms in after it (target 11). Shorter makes it static, longer makes it a slow swell. |
| `bloomRel` | 150 ms | Chosen | The discharge time constant. Long enough that the asymmetry outlasts a loud passage and colours the quieter notes after it, short enough to clear within a second (target 12). Typical valve coupling and grid-leak time constants are of this order, but the value here is a design choice, not taken from any circuit. |
| Shift law | −`bloomMax` · tanh(max(0, \|x\| − `bloomThr`) / `bloomThr`), smoothed | Chosen | Each sample's excess over the knee sets a target that saturates at `bloomMax`, and the smoother after it sets the timing whatever the Drive. Smoothing before the saturation made the full shift arrive on the first cycle at high Drive. |

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

9. Bloom changes nothing below the diode knee: a −40 dBFS 220 Hz tone renders bit-identically at Bloom 0 and 100 at Drive 0, 50 and 100. Measured: identical.
10. On a −12 dBFS 220 Hz tone, Bloom 100 gives H2 above −35 dBc and at least 30 dB above Bloom 0, at Drive 50 and 100. Measured: −19.9 dBc and −31.2 dBc, against −84 dBc (the analysis floor) at Bloom 0.
11. The second harmonic builds up: it reaches within 3 dB of its steady value between 10 ms and 100 ms after the onset. Measured: 34 ms at Drive 50 and 22 ms at Drive 100, with an 18 ms analysis window. On a plucked 110 Hz note at Drive 50 it peaks 48 ms into the note (target: later than 30 ms).
12. It outlasts the loud passage: 100 ms after the step down to −40 dBFS, H2 is at least 20 dB above Bloom 0. 1.2 s after, it is below −60 dBc. Measured: −41.4 dBc and −24.8 dBc at 100 ms (Drive 50 and 100), −85 dBc and −89 dBc at 1.2 s.
13. Cleanup curve at Drive 50: no H2 above −80 dBc for inputs of −40 dBFS or less, and above −30 dBc somewhere in the playing range. Measured: −163 dBc at most below −40 dBFS, and a peak of −19.9 dBc near −12 dBFS. H3 is the same at Bloom 0 and 100.
14. With Bloom 100 at Drive 100, the worst alias for a 1.1 kHz tone is below −60 dBc. Measured: −84.5 dBc (−38.5 dBc at 1x). The control is held across the four phases of each sample, and this shows it is smooth enough for that.

Targets 9 to 14 are checked in `tests/midhump/test_dynamics.py`.

## 6. Open questions

Only listening can answer these.

- Is `cleanTrim` 0.5 the right amount? Does Blend near 100 % sound hollow because of the phase difference between the clean and driven paths? Measurement shows the clean path is time-aligned, but the driven path itself is up to 90° from the input in the bass (target 7 above), so the two add in partial quadrature there.
- Does the soft 0.6 V knee (`Vd`) sound like the pedal at low Drive?
- Does the log Drive law put the useful range where a player expects it?
- Does the behavioural Tone shelf feel as wide as the pedal's?
- Does Bloom read as a player expects? Measurement shows when the second harmonic arrives and how long it stays, but not whether it feels like the drive responding to the hand or like an effect on top of it. The constants to change are `bloomAtt`, `bloomRel` and `bloomMax`.
- At high Drive, the quiet notes after a loud passage carry more H2 than the loud passage itself (−20 dBc against −31 dBc at Drive 100), because hard clipping squares both halves off whatever the bias. Is that a welcome “sag” or does it sound like the drive misbehaving?
- Should Bloom's time constants scale with Drive, as a real stage's would with its operating point?
