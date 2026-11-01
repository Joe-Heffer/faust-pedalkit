# BassEras

A bass preamp and DI built around one knob. **Character** re-voices the whole preamp at once: below noon it scoops the low mids for a deep, big-stack sound; at noon it is flat and warm; above noon it pushes the upper mids, adds gain, and lets hard notes push the second clipping stage off centre, so a note's body blooms with second harmonic just after the attack. Drive, Bite, a clean Blend, a three-band EQ and a speaker sim complete it.

It borrows its control set and signal chain from a bass preamp/DI pedal whose Character knob sweeps through amp voicings of several eras. That pedal's circuit is not public, so the stages are chosen. See the [design notes](design-notes.md) for the idea and the [circuit notes](circuit-notes.md) for what is borrowed.

## Download

<!-- downloads:basseras -->

## Details

| Property | Value |
|---|---|
| Source | [`src/basseras.dsp`](https://github.com/Joe-Heffer/faust-pedalkit/blob/main/src/basseras.dsp) |
| Plugin URI | `urn:pedalkit/basseras` |
| LV2 class | Amplifier |
| Channels | Mono in, mono out |
| Latency | 64 samples (1.33 ms at 48 kHz), reported to the host |
| Research | [Circuit notes](circuit-notes.md), [design notes](design-notes.md) |

## Controls

| Control | Range | Default | What it does |
|---|---|---|---|
| Level | −40 to +12 dB | 0 dB | Output level |
| Blend | 0 to 100 % | 100 % | 0 = clean only (the EQ and Level stay active), 100 = preamp only |
| Drive | 0 to 100 % | 30 % | Gain into the two clipping stages, 0 to 30 dB |
| Character | 0 to 100 % | 50 % | Pre-clip mid cut (−15 dB near 250 Hz) at 0, flat at 50, mid boost (+15 dB near 700 Hz) with up to 12 dB more gain and the bias bloom at 100 |
| Low | −12 to +12 dB | 0 dB | Shelf at 125 Hz |
| Mid | −12 to +12 dB | 0 dB | Band at 1 kHz |
| High | −12 to +12 dB | 0 dB | Shelf at 3.2 kHz |
| Bite | 0 to 100 % | 100 % | Subsonic high-pass before the clipping (10 Hz up to 40 Hz) and a presence peak after it (up to +6 dB at 2.5 kHz). Continuous, where the pedal has a switch |
| Cab Bypass | off / on | off | Removes the speaker sim from the preamp path, for a cabinet or an impulse response. Crossfaded, so it doesn't click |

Every control is smoothed. The plugin also has a read-only *Latency* output for the host. The LV2, VST3 and CLAP plugins ship with [eight factory presets](#presets).

## Presets

Each preset sets every control. Level is set so that a −12 dBFS plucked bass line (E1 to G2) comes out within 0.05 dB of "Studio Flip" (K-weighted), so switching presets doesn't jump in loudness. Bite is on and the speaker sim is in every preset.

| Preset | Level | Blend | Drive | Character | Low | Mid | High | Idea |
|---|---|---|---|---|---|---|---|---|
| Studio Flip | 0 | 100 | 30 | 50 | 0 | 0 | 0 | The defaults: warm, flat, light grit |
| Clean DI | 0 | 0 | 30 | 50 | 0 | 0 | 0 | Preamp bypassed; EQ and Level only |
| Seventies Stack | −4.2 | 100 | 45 | 20 | +3 | +2 | −2 | Deep and scooped in the low mids |
| Thumpy Funk | +2.9 | 80 | 15 | 35 | +4 | −3 | +3 | Hollow, percussive attack |
| Fat Tube | −7.4 | 100 | 55 | 60 | +2 | 0 | −3 | Thick, rounded breakup |
| Warm Compression | −4.0 | 70 | 60 | 40 | +1 | 0 | −2 | Clipping evens the level; clean keeps the attack |
| Modern Crunch | −8.8 | 100 | 60 | 80 | 0 | +2 | +2 | Pushed upper mids and the bloom |
| Fuzzed Out | −10.8 | 85 | 90 | 100 | +3 | −2 | 0 | Heavy, compressed distortion |

Levels and EQ are in dB, the rest in %. The names follow the kinds of sound the reference pedal's manual suggests, but the settings are chosen, not taken from it, and nobody has listened to them. They live in [`src/basseras.presets.toml`](https://github.com/Joe-Heffer/faust-pedalkit/blob/main/src/basseras.presets.toml).

[![Long-term third-octave spectrum of a plucked bass line through each preset](../measurements/basseras/presets_spectrum.svg)](../measurements/basseras/presets_spectrum.svg "Open the full-size plot")

Data: [`presets_spectrum.csv`](../measurements/basseras/presets_spectrum.csv) (`preset, band_hz, level_db`) and [`presets_levels.csv`](../measurements/basseras/presets_levels.csv) (`preset, loudness_rel_db, peak_dbfs, square_peak_dbfs`).

## Signal path

```text
in → DC blocker (5 Hz)
   ├─ clean: delay 64 samples ───────────────────────────────────────────────┐
   └─ preamp: Bite subsonic high-pass (10 → 40 Hz)                            │
        → Character mid EQ (250 → 700 Hz, ±15 dB) → gain (Drive, + Character) │
        → 4x oversampled soft clip (±1.2 V) → 6 kHz low-pass                  Blend
        → ×4 → 4x oversampled rail clip (±3.1 V), biased by hard notes        │
        → DC blocker (5 Hz) → Bite presence (2.5 kHz)                         │
        → speaker sim (or Cab Bypass) → trim ─────────────────────────────────┘
→ Low (125 Hz) → Mid (1 kHz) → High (3.2 kHz) → Level → safety limiter (≤ −0.1 dBFS) → out
```

The [schematic](../development/schematics.md) draws each stage as a standard analogue stand-in, one sheet per stage, listed in section 4 of the [circuit notes](circuit-notes.md). Nothing in it is a trace of the pedal. The root sheet:

![Root sheet: the block diagram, one hierarchical sheet per stage](../schematics/basseras/basseras.svg)

## Measured behaviour

These figures come from `make test` at 48 kHz. The plots below are regenerated each time the site is published. Click a plot to open it full size; the CSV data behind each one is linked underneath.

### Summary

- **Silence in gives silence out.** Below −120 dBFS at 288 combinations of extreme settings.
- **Peak level.** With 0 dBFS square waves, noise, sweeps or impulses in and every control at maximum, the worst sample is −0.10 dBFS.
- **Clean path.** With Blend 0 and a flat EQ the response is within 0.09 dB from 30 Hz to 15 kHz.
- **EQ.** Mid reaches ±12.0 dB at 1 kHz. Low and High are ±5.9 dB at their corners and ±11.7 to 12.0 dB a factor of 3 beyond; cut mirrors boost.
- **Character.** The pre-clip EQ lands within 0.1 dB and 1 % of its design: −15.0 dB at 252 Hz (Character 0) to +15.0 dB at 697 Hz (Character 100). At Drive 30, THD rises from 0.8 % (Character 0) and 5.7 % (50) to 34.3 % (100).
- **Bloom.** At Character 100 a hard 110 Hz note carries second harmonic at −25.5 dBc (−84.2 dBc at Character 50). It builds over 33 ms, is still 25 dB above Character 50 100 ms after the note, and is gone (−80.8 dBc) 1.1 s later.
- **Bite.** −15.6 dB at 15 Hz, +6.0 dB at 2.5 kHz, within 0.27 dB from 100 to 500 Hz. At full Drive it lowers the intermodulation of a 15 Hz rumble with a note by 25 dB.
- **Speaker sim.** −3 dB at 3.72 kHz, −28 dB at 10 kHz, no peak (+0.07 dB). Cab Bypass is within 0.8 dB of the voiced loudness at every setting measured.
- **Limiting.** At Drive 100 the output rises 0.01 dB per dB from −20 to 0 dBFS in.
- **Aliasing.** At full Drive, Character and Bite, 4x oversampling lowers the worst alias by 49.7 dB at 441 Hz (to −89.9 dBc) and 21.5 dB at 1.1 kHz (to −52.2 dBc) against a 1x build.
- **CPU.** About 2.3 % of one core at 48 kHz at the defaults, 2.7 % with every control at maximum.

### Frequency response

[![Frequency response of BassEras against Drive, the speaker sim, the EQ and the Blend](../measurements/basseras/freqresp.svg)](../measurements/basseras/freqresp.svg "Open the full-size plot")

Data: [`freqresp.csv`](../measurements/basseras/freqresp.csv) (`panel, input_dbfs, blend, drive, character, low, mid, high, bite, cab_bypass, freq_hz, gain_db`).

### Character

[![Character EQ relative to noon, and THD against Character](../measurements/basseras/character.svg)](../measurements/basseras/character.svg "Open the full-size plot")

Data: [`character.csv`](../measurements/basseras/character.csv) (`test, character, x, value_db`).

### Dynamics: the bloom

[![Second harmonic over time for a loud burst and a pluck, and output against input level](../measurements/basseras/dynamics.svg)](../measurements/basseras/dynamics.svg "Open the full-size plot")

Data: [`dynamics.csv`](../measurements/basseras/dynamics.csv) (`test, setting, series, x, value_db`).

### Bite

[![Bite relative to Bite 0](../measurements/basseras/bite.svg)](../measurements/basseras/bite.svg "Open the full-size plot")

Data: [`bite.csv`](../measurements/basseras/bite.csv) (`bite, x, value_db`).

### Cab Bypass

[![Loudness of the bypassed preamp path minus the voiced one](../measurements/basseras/cabsim.svg)](../measurements/basseras/cabsim.svg "Open the full-size plot")

Data: [`cabsim.csv`](../measurements/basseras/cabsim.csv) (`character, drive, bypassed_minus_voiced_db`).

### Harmonics and aliasing

[![Harmonic levels against Drive and Character, and the alias spectrum of a 1.1 kHz tone](../measurements/basseras/harmonics.svg)](../measurements/basseras/harmonics.svg "Open the full-size plot")

Data: [`harmonics.csv`](../measurements/basseras/harmonics.csv) (`f0_hz, drive, character, harmonic, level_dbc`) and [`aliasing.csv`](../measurements/basseras/aliasing.csv) (`build, cab_bypass, f0_hz, worst_alias_dbc`).

## What to tune by ear

Nothing has been listened to. The constants are in `src/basseras.dsp`, and the [design notes](design-notes.md) give the intent of each.

1. The Character sweep: its direction, its ends (`charFLo` 250 Hz, `charFHi` 700 Hz), `charQ` (0.7) and `charGainDb` (12 dB).
2. The bloom: `bloomMax` (0.25 × `railV`), `bloomAtt` (20 ms) and `bloomRel` (150 ms). Keep `bloomMax` at or below 0.25 × `railV`, or a sudden Character jump clicks.
3. The speaker sim: `cabLp1F` (4.5 kHz), `cabLp2F` (6 kHz) and `cabHpF` (30 Hz).
4. Bite: `biteHpHi` (40 Hz), `presF` (2.5 kHz) and `presDb` (+6 dB).
5. The clipping: `v1` (±1.2 V), `g2` (4), `railN` (4), `interLp` (6 kHz) and `driveMaxDb` (30 dB).
6. `drvTrim` (0.42) and the default Drive (30 %).

## Known limitations

- **Not a model of the pedal.** Its clipping stages are in a sealed module, and no schematic is public, so every stage is chosen. Only the control set, the EQ frequencies and range, and the order of the stages come from sources.
- **The Character sweep is a guess.** The direction of the cut and boost, and the moving centre, are not documented.
- **The schematic is a stand-in.** It draws the Character centre at noon only, and first-order shelves where the DSP has second-order ones.
- **Not modelled:** the pedal's XLR pad, +10 dB switch, parallel output, phantom power and ground lift.
- **Mono only.**

BassEras is an independent design built from public information. It is not affiliated with, or endorsed by, any pedal manufacturer.
