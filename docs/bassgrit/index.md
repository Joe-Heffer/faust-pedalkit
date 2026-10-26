# BassGrit

A hard-clipping distortion for bass. It borrows the sound of a classic op-amp distortion pedal (a very high-gain stage that darkens as the gain rises, diodes clipping to ground, and a low-pass that gets darker as it is turned up) and adds what a bass needs: the signal is split at a **Crossover**, and only the upper band is clipped. The low band stays clean and comes back at **Low Blend**, so the fundamental stays tight while the harmonics get the full treatment.

| Property | Value |
|---|---|
| Source | [`src/bassgrit.dsp`](https://github.com/Joe-Heffer/faust-pedalkit/blob/main/src/bassgrit.dsp) |
| Plugin URI | `urn:pedalkit/bassgrit` |
| LV2 class | Distortion |
| Channels | Mono in, mono out |
| Latency | 32 samples (0.67 ms at 48 kHz), reported to the host |
| Research | [Circuit notes](circuit-notes.md), [design notes](design-notes.md) |

## Controls

| Control | Range | Default | What it does |
|---|---|---|---|
| Distortion | 0 to 100 % | 50 % | Gain of the op-amp stage, from unity to about 67 dB at high frequencies, with an audio (log) taper. Higher settings also lower the stage's bandwidth. |
| Filter | 0 to 100 % | 30 % | Low-pass after the diodes, from 22.6 kHz down to 334 Hz. Turning it up darkens the sound, as on the pedal. |
| Level | −40 to +12 dB | 0 dB | Output level |
| Low Blend | 0 to 100 % | 70 % | Clean signal below the Crossover. 100 % makes the response flat at Distortion 0. |
| Crossover | 40 to 400 Hz | 120 Hz | Below this the signal bypasses the clipper (4th-order Linkwitz-Riley) |

Every control is smoothed. The plugin also has a read-only *Latency* output for the host. There are no factory presets yet.

## Signal path

```text
in → DC blocker (5 Hz)
   ├─ low band:  4th-order low-pass (Crossover) → delay 32 samples → × Low Blend ─────┐
   └─ high band: 4th-order high-pass (Crossover)                                      │
        → op-amp stage: input + branch (47 Ω/2.2 µF and 560 Ω/4.7 µF legs,           │
          feedback pole, gain-bandwidth pole)                                         │
        → 4x oversampled hard diode clip (0.6 V) → Filter low-pass ───────────────────┤
→ sum → × 1.2 → Level → safety limiter (≤ −0.1 dBFS) → out
```

The schematic is not drawn yet; see [known limitations](#known-limitations).

## Measured behaviour

These figures come from `make test` at 48 kHz. The plots below are regenerated each time the site is published. Click a plot to open it full size; the CSV data behind each one is linked underneath.

### Summary

- **Silence in gives silence out.** The output stays below −120 dBFS at 16 combinations of extreme settings.
- **Peak level.** With 0 dBFS square waves, noise, sweeps or impulses in, at every Low Blend and Crossover tried, the worst sample is −0.10 dBFS.
- **Flat at Distortion 0.** With Filter 0 and Low Blend 100 the response is within 0.21 dB of its 1.6 dB trim from 30 Hz to 8 kHz.
- **Clean fundamental.** At Distortion 50 the 41 Hz gain moves +0.7 dB while 1 kHz rises +41.1 dB. A 41 Hz tone at −12 dBFS has THD of −77.2 dB, against −11.6 dB with the Crossover at 40 Hz.
- **Gain-bandwidth limit.** At Distortion 100, 5 kHz is 8.9 dB below 1 kHz. At Distortion 50 it is 1.7 dB above.
- **Odd-order distortion.** The clipper is symmetric: even/odd −81.7 dB at 110 Hz and −89.8 dB at 220 Hz.
- **Aliasing.** Against a 1x build at Distortion 100, 4x oversampling lowers the worst alias by 42.5 dB at 221 Hz and 24.0 dB at 441 Hz, where it is −61.5 dBc. At 1.1 kHz it is −45.8 dBc and at 3.7 kHz −34.5 dBc: a near-square wave cannot be made alias-free by 4x oversampling.

### Frequency response

[![Frequency response of BassGrit at several Distortion, Filter and Crossover settings](../measurements/bassgrit/freqresp.svg)](../measurements/bassgrit/freqresp.svg "Open the full-size plot")

Data: [`freqresp.csv`](../measurements/bassgrit/freqresp.csv) (columns `panel, input_dbfs, setting, freq_hz, gain_db`).

- **Distortion (top left, −70 dBFS noise).** The low end stays at about 0 dB and the gain hump rises and moves down in frequency, from a 1.6 dB plateau at Distortion 0 to a 55 dB peak near 800 Hz at Distortion 100. The top rolls off earlier at high settings (the gain-bandwidth pole).
- **Louder input (top right, −20 dBFS).** The diodes compress the hump to about 15 dB to 25 dB.
- **Filter (bottom left).** Only the top changes: the corner moves from above 20 kHz to about 330 Hz.
- **Crossover (bottom right).** The knee between the clean low band and the driven band moves from 60 Hz to 400 Hz.

### Harmonics and aliasing

[![Harmonic levels for 110 Hz and 220 Hz tones at three Distortion settings, and the alias spectrum of a 441 Hz tone](../measurements/bassgrit/harmonics.svg)](../measurements/bassgrit/harmonics.svg "Open the full-size plot")

Data: [`harmonics.csv`](../measurements/bassgrit/harmonics.csv) (`f0_hz, distortion, harmonic, level_dbc`) and [`aliasing.csv`](../measurements/bassgrit/aliasing.csv) (`build, f0_hz, worst_alias_dbc`).

Only odd harmonics appear. At 110 Hz, H3 is −24 dBc at Distortion 25 and about −10 dBc at 100, and the higher odd harmonics fill in as Distortion rises.

### Design targets

[![Small-signal response at three Distortion settings](../measurements/bassgrit/targets.svg)](../measurements/bassgrit/targets.svg "Open the full-size plot")

Data: [`targets.csv`](../measurements/bassgrit/targets.csv) (`quantity, value`). The eight targets are listed with their measured values in section 5 of the [design notes](design-notes.md).

## What to tune by ear

These values are chosen or inferred, and nothing has been listened to. The constants are in `src/bassgrit.dsp`.

1. Crossover default (120 Hz), and its slope.
2. `Cfilt` (4.7 nF): the Filter range.
3. `Vd` (0.6 V) and `nKnee` (4): the clipping level and hardness.
4. The Distortion law (`Rf`): where in the travel the gain rises.
5. `GBW` (1 MHz): how early the top rolls off at high Distortion.
6. `outTrim` (1.2) and the input level convention: 0 dBFS is treated as 1 V at the input.

## Known limitations

- **Component values are unchecked.** The [circuit notes](circuit-notes.md) were written without access to a schematic. Several values are recalled, not sourced.
- **No schematic yet.** KiCad was not available when this effect was written.
- **Not a circuit simulation.** The diodes are a static knee, and the op-amp's rail and slew limits are not modelled.
- **Full Distortion is not alias-clean above about 500 Hz.**
- **At Distortion 100 the lowest octave is not fully clean:** the clipper's gain from 60 Hz leaves a lift of only 3.4 dB from Low Blend at 30 to 60 Hz.
- **Mono only.**

BassGrit is an independent design built from public information. It is not affiliated with, or endorsed by, any pedal manufacturer.
