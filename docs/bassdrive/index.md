# BassDrive

A bass overdrive with a clean/driven blend and a two-band EQ, modelled on a classic compact bass overdrive pedal. The full-range clean path keeps the low end solid while the driven path adds grind on top.

| Property | Value |
|---|---|
| Source | [`src/bassdrive.dsp`](https://github.com/Joe-Heffer/faust-pedalkit/blob/main/src/bassdrive.dsp) |
| Plugin URI | `urn:pedalkit/bassdrive` |
| LV2 class | Distortion |
| Channels | Mono in, mono out |
| Latency | 32 samples (0.67 ms at 48 kHz), reported to the host |
| Research | [Circuit notes](circuit-notes.md) |
| Try it | [Browser demo](../demo/index.html) (no install; see [how it works](../usage/browser.md)) |

## Controls

| Control | Range | Default | What it does |
|---|---|---|---|
| Level | −40 to +12 dB | 0 dB | Output level |
| Balance | 0 to 100 % | 50 % | 0 = clean only, 100 = driven only. The clean path is full-range, so the low end holds up as Gain rises. |
| Gain | 0 to 100 % | 50 % | Drive amount, with an audio (log) taper |
| Bass | −12 to +12 dB | 0 dB | Peaking band at 110 Hz |
| Treble | −15 to +15 dB | 0 dB | High shelf from 2.5 kHz |

Every control is smoothed, so automating or turning them does not zipper. The plugin also has a read-only *Latency* output for the host's delay compensation.

!!! tip "Getting the original's voicing"
    On the original pedal, the High control already gives about +10 dB at noon. Here 0 dB on Bass and Treble is flat, apart from the fixed mid scoop. For the original's voicing, start from **Treble +10 dB**.

## Signal path

```text
in → DC blocker (5 Hz)
   ├─ clean:  delay 32 samples
   └─ driven: stage 1 pre-emphasis gain
              → 4x oversampled clipper
              → DC blocker → 5 kHz low-pass → trim
→ Balance (clean/driven blend)
→ Bass (110 Hz) → fixed mid scoop (−6 dB at 350 Hz) → Treble (2.5 kHz shelf)
→ Level → safety limiter (≤ −0.1 dBFS) → out
```

- **Stage 1** is a non-inverting gain stage with a series RC shunt (3.3 kΩ and 33 nF, a corner at about 1.46 kHz). Bass notes pass at roughly unity while the upper register is driven hard, which gives the pedal's "treble layer over the clean tone" character.
- **The clipper** has a soft tanh knee at +1.7 V (a red LED) and a harder knee at −0.8 V (a biased transistor stage running out of headroom). The distortion is light and odd-order at low Gain and leans even-order by noon, as the reference measurements report.
- **The clean path** is only delayed by the oversampler's latency, so the blend doesn't comb-filter.

The [circuit notes](circuit-notes.md) give the derivation of every stage and the confidence level of each value.

## Measured behaviour

These figures come from `make test` at 48 kHz. The plots below are regenerated each time the site is published. Click a plot to open it full size; the CSV data behind each one is linked underneath.

### Summary

- **Silence in gives silence out.** The output stays below −120 dBFS at all 48 combinations of extreme settings.
- **Peak level.** With every control at maximum and 0 dBFS square waves, noise, sweeps or impulses in, the worst sample is −0.10 dBFS.
- **The low end holds up.** At Balance 50 %, the low E fundamental (41 Hz) varies by only 1.4 dB across the whole Gain range. The clean path alone is flat within ±1.5 dB from 30 to 100 Hz.
- **Fixed mid scoop.** About 5–6 dB at 350 Hz, matching the published measurement of the original.
- **Aliasing.** Against a 1x build of the same DSP at full Gain, 4x oversampling lowers the worst alias by 22 dB for a 3.7 kHz tone and by 30 dB for a 1.1 kHz tone. The worst alias at 1.1 kHz is −65 dBc.

### Frequency response

[![Frequency response of BassDrive at several Gain, Balance and EQ settings](../measurements/bassdrive/freqresp.svg)](../measurements/bassdrive/freqresp.svg "Open the full-size plot")

Data: [`freqresp.csv`](../measurements/bassdrive/freqresp.csv) (columns `panel, input_dbfs, balance, gain, bass, treble, freq_hz, gain_db`).

- **Driven path (Balance 100 %, top left).** For small signals, the response rises from about 300 Hz to a broad peak at 1–3 kHz. The peak grows with Gain: about +3 dB at Gain 0, +25 dB at noon and +36 dB at maximum. Above about 5 kHz it falls steeply. This is the treble-forward, "grind on top of the clean low end" voicing the original is known for.
- **The blend (Balance 50 %, middle).** The clean and driven paths cancel at one frequency in the upper treble, around 6–8 kHz. This is a property of summing these two paths, and is worth listening for (see [What to tune by ear](#what-to-tune-by-ear)).
- **Louder input (−20 dBFS, bottom row).** The clipper compresses the driven path, so the curves bunch together as Gain rises.
- **EQ only (Balance 0 %, top right).** The Bass peak at 110 Hz, the Treble shelf from 2.5 kHz with its 12 kHz cap, and the fixed 350 Hz scoop present at every setting.

### Harmonics and aliasing

[![Harmonic levels for 41 Hz and 110 Hz tones at three Gain settings, and the alias spectrum of a 3.7 kHz tone](../measurements/bassdrive/harmonics.svg)](../measurements/bassdrive/harmonics.svg "Open the full-size plot")

Data: [`harmonics.csv`](../measurements/bassdrive/harmonics.csv) (`f0_hz, gain, harmonic, level_dbc`) and [`aliasing.csv`](../measurements/bassdrive/aliasing.csv) (`build, f0_hz, worst_alias_dbc`).

Single sines at −12 dBFS, driven path only:

| Gain | 41 Hz THD | 110 Hz THD | Character |
|---|---|---|---|
| 0 % | 2.2 % | 1.4 % | Light, odd-order |
| 50 % | 5.9 % | 12.5 % | H2 overtakes H3 at 110 Hz: warm, even-leaning |
| 100 % | 30.5 % | 27.5 % | Heavy, odd-order dominant, harmonics strong up to the 10th |

The right-hand panel compares a 1x build with the 4x-oversampled plugin for a 3.7 kHz tone at full Gain. The aliases are the components that fall between the harmonics.

### Sweeps and low-end retention

[![Spectrograms of a log sweep through the driven path at three Gain settings, output level against sweep frequency, and the 41 Hz fundamental against Gain and Balance](../measurements/bassdrive/sweep_lowE.svg)](../measurements/bassdrive/sweep_lowE.svg "Open the full-size plot")

Data: [`sweep_level.csv`](../measurements/bassdrive/sweep_level.csv) (`gain, freq_hz, level_db`) and [`lowE_fundamental.csv`](../measurements/bassdrive/lowE_fundamental.csv) (`sweep, setting, fundamental_dbfs`).

The spectrograms show the harmonics spreading as Gain rises. The bottom row shows the level of the 41 Hz fundamental: it stays within about 1.4 dB across the whole Gain range at Balance 50 %, which is what the clean blend is for.

## What to tune by ear

These are measured approximations that have not been listening-tested. Each item names the control or `src/bassdrive.dsp` constant to change.

1. **The blend notch.** With Balance near 50 % and Gain high, the two paths cancel at about 6–8 kHz. Listen for a hollow or phasey top end. `postLP` moves the notch, and `drvTrim` changes its depth.
2. **How lopsided the drive is.** `ledNeg` (0.8 V) and `negKnee` (6) set how quickly the sound turns warm and even-order as Gain rises. Raise `ledNeg` towards 1.7 for a more symmetric, harder sound.
3. **Overall drive range.** `stage2G` (3.0) and the 303 in `hfGain` set how much distortion there is at each Gain position.
4. **The mid scoop.** `scoopDB` (−6 dB). Try −3 dB for a fuller mix sound, or 0 to remove it.
5. **Fizz.** `postLP` (5 kHz) and Treble. If high Gain sounds buzzy, lower `postLP` towards 3.5 kHz.
6. **Clean/driven loudness.** `drvTrim` (0.28). Set it so that sweeping Balance at your usual Gain doesn't change the perceived volume.
7. **Input level.** The model treats 0 dBFS as 1 V at the pedal's input. If your interface records the bass hot or quiet, every Gain setting will feel shifted, so adjust your input gain before changing the constants.

## Known limitations

- **It isn't a full circuit simulation.** The drive stage is modelled as linear filters around a memoryless waveshaper. Effects that depend on the circuit's history are not captured: bias shifting under heavy playing, supply sag, and interaction between the clipper and the filters around it. Fast transients therefore compress a little more neatly than real hardware does.
- **Several values are educated guesses.** The Gain pot taper and range, the stage-2 gain, the clipping asymmetry and the post-filter are all marked "chosen" in the [circuit notes](circuit-notes.md). All of them are named constants near the top of `src/bassdrive.dsp`.
- **Maximum Gain is more odd-order than the reference.** The reference measurement describes that setting as "sawtooth-like", which suggests more even-order content than the model produces.
- **The tone stack doesn't interact.** The EQ bands are independent digital filters, whereas a passive or active network would interact.
- **Mono only.**
- **Low sample rates shift the top end.** Below about 27 kHz the 12 kHz treble cap, and below about 11 kHz the 5 kHz post-filter, are held at 0.45 × the sample rate to stay stable, so the response above them differs from the 48 kHz plots. `test_samplerates.py` checks that the output stays finite and within 6 dB at 110 Hz from 8 kHz to 192 kHz.
- **Some aliasing remains.** At extreme Gain with very high-pitched material, some aliasing remains despite the 4x oversampling. The safety limiter runs at the base rate and can alias if you drive it hard with Level.

BassDrive is an independent model built from public information. It is not affiliated with, or endorsed by, any pedal manufacturer.
