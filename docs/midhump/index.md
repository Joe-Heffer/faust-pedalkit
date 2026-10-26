# MidHump

A mid-hump overdrive. Mids are driven into soft diode clipping while bass passes at unity gain, which keeps the low end tight. An optional clean Blend, which the original circuit does not have, brings back the full range.

| Property | Value |
|---|---|
| Source | [`src/midhump.dsp`](https://github.com/Joe-Heffer/faust-pedalkit/blob/main/src/midhump.dsp) |
| Plugin URI | `urn:pedalkit/midhump` |
| LV2 class | Distortion |
| Channels | Mono in, mono out |
| Latency | 32 samples (0.67 ms at 48 kHz), reported to the host |
| Research | [Circuit notes](circuit-notes.md), [design notes](design-notes.md) |

## Controls

| Control | Range | Default | What it does |
|---|---|---|---|
| Drive | 0 to 100 % | 50 % | Clipping-stage gain, from about 21 dB to about 41 dB, with an audio (log) taper |
| Tone | 0 to 100 % | 50 % | Treble shelf after the 723 Hz low-pass, about 13 dB of range (a stand-in for the pedal's tone network; see [limitations](#known-limitations)) |
| Level | −40 to +12 dB | 0 dB | Output level |
| Blend | 0 to 100 % | 0 % | Adds a full-range clean signal. 0 is the circuit as published. |

Every control is smoothed. The plugin also has a read-only *Latency* output for the host.

## Presets

The LV2, VST3 and CLAP plugins all ship with the same factory presets. They are starting points chosen by measurement, not by ear. Each one sets every control, and Level is set so that a −12 dBFS plucked guitar line comes out within 0.05 dB of "Edge of Breakup" (K-weighted), so switching presets doesn't jump in loudness.

| Preset | Drive | Tone | Level | Blend | Idea |
|---|---|---|---|---|---|
| Edge of Breakup | 10 | 40 | 0 | 0 | Light odd-harmonic grit for pushing an amplifier |
| Mid Hump | 50 | 50 | −2 | 0 | The defaults: the reference circuit at mid Drive and Tone |
| Lead | 100 | 65 | −6.4 | 0 | Full Drive with a brighter Tone, for sustained single notes |
| Bass Grind | 60 | 40 | −3.6 | 100 | Mid-hump drive on bass, with the full clean Blend to keep the lowest octave |

Levels are in dB, the rest in %. The presets live in [`src/midhump.presets.toml`](https://github.com/Joe-Heffer/faust-pedalkit/blob/main/src/midhump.presets.toml).

[![Long-term third-octave spectrum of a plucked guitar line through each preset](../measurements/midhump/presets_spectrum.svg)](../measurements/midhump/presets_spectrum.svg "Open the full-size plot")

Data: [`presets_spectrum.csv`](../measurements/midhump/presets_spectrum.csv) (`preset, band_hz, level_db`) and [`presets_levels.csv`](../measurements/midhump/presets_levels.csv) (`preset, loudness_rel_db, peak_dbfs, square_peak_dbfs`).

## Signal path

```text
in → input high-pass (15.6 Hz)
   ├─ clean:  delay 32 samples → × Blend × 0.5 ──────────────────────────┐
   └─ clipping stage: input + 4x oversampled diode clip of               │
        (720 Hz high-pass → feedback low-pass → gain 11.9 to 118)        │
      → 723 Hz low-pass → Tone shelf → DC blocker (5 Hz) ────────────────┤
→ sum → Level → safety limiter (≤ −0.1 dBFS) → out
```

## Measured behaviour

These figures come from `make test` at 48 kHz. The plots below are regenerated each time the site is published. Click a plot to open it full size; the CSV data behind each one is linked underneath.

### Summary

- **Silence in gives silence out.** The output stays below −120 dBFS at 16 combinations of extreme settings.
- **Peak level.** With 0 dBFS square waves, noise, sweeps or impulses in, at every Blend setting, the worst sample is −0.10 dBFS. The plugin is finite and bounded at every sample rate from 8 kHz to 192 kHz.
- **The model matches its equations.** The small-signal response is within 0.16 dB of the analytic circuit model from 50 Hz to 4 kHz at Drive 0, 50 and 100.
- **Mid hump.** At Drive 100 the response peaks at 826 Hz, with 100 Hz 12.1 dB below the peak. Gain at 2 kHz runs from 20.9 dB at Drive 0 to 40.4 dB at Drive 100.
- **Odd-order distortion.** The clipper is symmetric, and even harmonics stay at the float noise floor.
- **Aliasing.** Against a 1x build at Drive 100, 4x oversampling lowers the worst alias by 24.5 dB for a 3.7 kHz tone and by 46.0 dB for a 1.1 kHz tone. The worst alias at 1.1 kHz is −83.3 dBc.

### Frequency response

[![Frequency response of MidHump at several Drive, Tone and Blend settings](../measurements/midhump/freqresp.svg)](../measurements/midhump/freqresp.svg "Open the full-size plot")

Data: [`freqresp.csv`](../measurements/midhump/freqresp.csv) (columns `panel, input_dbfs, drive, tone, blend, freq_hz, gain_db`).

- **Drive (top left, −70 dBFS noise).** A broad hump centred near 830 Hz, from about +16 dB at Drive 0 to +36 dB at Drive 100. Below it the response falls at about 6 dB/octave towards unity, and above it the 723 Hz low-pass takes over. At Drive 100 the C4 feedback low-pass (5.7 kHz) also pulls the top end down.
- **Louder input (top right, −20 dBFS).** The diodes compress the hump to about +10 to +15 dB, and the Drive curves bunch together.
- **Tone (bottom left).** Tone only changes the response above about 500 Hz, from a peak of 35 dB at 0 % to 39 dB at 100 %, with the peak moving up to about 1.4 kHz.
- **Blend (bottom right).** At small signals the clean path adds 0.5 times the input, time-aligned. The lift below 100 Hz is small here because the unclipped branch is already large there. At −20 dBFS, where the branch clips, Blend 100 % lifts 30 Hz to 60 Hz by 2.6 dB to 3.1 dB across the Drive range.

### Harmonics and aliasing

[![Harmonic levels for 110 Hz and 220 Hz tones at three Drive settings, and the alias spectrum of a 3.7 kHz tone](../measurements/midhump/harmonics.svg)](../measurements/midhump/harmonics.svg "Open the full-size plot")

Data: [`harmonics.csv`](../measurements/midhump/harmonics.csv) (`f0_hz, drive, harmonic, level_dbc`) and [`aliasing.csv`](../measurements/midhump/aliasing.csv) (`build, f0_hz, worst_alias_dbc`).

Single sines at −12 dBFS, Tone 50 %:

| Drive | 110 Hz THD | 220 Hz THD | H3 at 110 Hz |
|---|---|---|---|
| 0 % | 2.5 % | 7.0 % | −32 dBc |
| 50 % | 8.0 % | 15.0 % | −22 dBc |
| 100 % | 30.5 % | 26.8 % | −12 dBc |

Only odd harmonics appear. 220 Hz distorts more than 110 Hz at low Drive, because more of it gets through the 720 Hz high-pass into the clipper.

### Sweeps and targets

[![Spectrograms of a log sweep at three Drive settings and output level against sweep frequency](../measurements/midhump/sweep.svg)](../measurements/midhump/sweep.svg "Open the full-size plot")

Data: [`sweep_level.csv`](../measurements/midhump/sweep_level.csv) (`drive, freq_hz, level_db`).

[![Measured response against the analytic model, the 1 kHz fundamental against input level, and the gain at 2 kHz against Drive](../measurements/midhump/targets.svg)](../measurements/midhump/targets.svg "Open the full-size plot")

Data: [`targets.csv`](../measurements/midhump/targets.csv) (`panel, setting, x, value`) and [`samplerates.csv`](../measurements/midhump/samplerates.csv) (`setting, sample_rate_hz, finite, peak_dbfs, rms_dbfs`).

The middle panel shows why the pedal never goes fully square: once the diodes conduct (about −40 dBFS in at Drive 100), the 1 kHz fundamental keeps rising with input, because the unclipped input is always part of the output.

## What to tune by ear

These values are chosen or inferred, and nothing has been listened to. The constants are in `src/midhump.dsp`.

1. `Vd` (0.6 V): the diode knee level. Lower gives more compression and earlier clipping.
2. The Drive law (`Rd`): where in the travel the gain rises.
3. `cleanTrim` (0.5): the size of the Blend path.
4. `fcZero` and `fcShelf`: the Tone shelf, which is a stand-in for the real tone network.
5. The input level convention: 0 dBFS is treated as 1 V at the input.

## Known limitations

- **Not a circuit simulation.** The diodes are a static soft clipper, and the feedback low-pass sits before them instead of acting on the clipped signal.
- **Tone is behavioural, and does not match the published description.** The shelf moves a zero from 3.29 kHz down to 723 Hz. The analysis it is meant to follow describes a cut at 3.2 kHz at one end of the pot and a boost there at the other. See section 7 of the [circuit notes](circuit-notes.md).
- **Input and output buffers and the op-amp's own limits are not modelled.**
- **Mono only.**

MidHump is an independent design built from public information. It is not affiliated with, or endorsed by, any pedal manufacturer.
