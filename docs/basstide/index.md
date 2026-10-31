# BassTide

A through-zero flanger for bass. Everything below the crossover stays dry, so the low end keeps its weight, and the harmonics above it go through a deep comb that sweeps through zero and back. With **Follow** up, the sweep follows your playing instead of an LFO: each note throws the comb out and it glides back to the zero point, where it vanishes, so the attack swooshes and the sustain is clean.

!!! warning "Draft"
    BassTide is an initial concept. It has not been compiled, tested or listened to yet, and the measurements below will appear once `make test` has run.

| Property | Value |
|---|---|
| Source | [`src/basstide.dsp`](https://github.com/Joe-Heffer/faust-pedalkit/blob/main/src/basstide.dsp) |
| Plugin URI | `urn:pedalkit/basstide` |
| LV2 class | Flanger |
| Channels | Mono in, mono out |
| Latency | 96 samples (2 ms at 48 kHz), the dry delay, reported to the host |
| Research | [Design notes](design-notes.md) |

## Download

<!-- downloads:basstide -->

## Controls

| Control | Range | Default | What it does |
|---|---|---|---|
| Rate | 0.05 to 5 Hz | 0.3 Hz | Speed of the steady LFO sweep |
| Sweep | 0 to 100 % | 70 % | How far the wet delay moves either side of the zero point: up to 2 ms ahead of the dry and 8 ms behind it |
| Follow | 0 to 100 % | 100 % | 0 is a steady LFO sweep. 100 lets each note start its own sweep, out behind the dry and back to the zero point. In between blends the two. |
| Glide | 50 ms to 2 s | 400 ms | Time scale of the note sweep: how long a note takes to sweep out and come back |
| Feedback | −90 to +90 % | 0 % | Feedback round the wet delay. Negative sounds hollow, positive rings |
| Depth | 0 to 100 % | 100 % | Notch depth. At 100 % wet and dry are equal and the notches are full nulls |
| Crossover | 80 to 400 Hz | 200 Hz | Below this the signal stays dry and unmodulated |
| Level | −20 to +12 dB | 0 dB | Output level, mainly for high Feedback |

Every control is smoothed. The plugin also has a read-only *Latency* output for the host.

## Signal path

```text
in → DC blocker (5 Hz)
   ├─ LR4 low-pass (Crossover) → delay 96 samples ─────────────────────────┐
   ├─ LR4 high-pass ┬─ delay 96 samples × (1 − Depth/2) ──────────────────┤
   │                └─ fractional delay 2 to 480 samples, Feedback × Depth/2 ┤
   └─ onset detector → note sweep ─┐                                        │
                         LFO (Rate) ┴→ Sweep × mix(LFO, note sweep; Follow) │
→ sum → Level → safety limiter (≤ −0.1 dBFS) → out
```

The dry signal is delayed by 96 samples, the through-zero point, and the host is told that as the latency, so the dry stays in time with the rest of a mix. The wet delay can be shorter than that, so the wet copy runs ahead of the dry, or longer, so it trails it. The [design notes](design-notes.md) give the reasoning and every constant.

## Measured behaviour

These figures will come from `make test` at 48 kHz.

### Frequency response

[![Frequency response of BassTide at rest and with Feedback](../measurements/basstide/freqresp.svg)](../measurements/basstide/freqresp.svg "Open the full-size plot")

Data: [`freqresp.csv`](../measurements/basstide/freqresp.csv) (`panel, depth, feedback, freq_hz, gain_db`).

### Sweep: through zero, and note by note

[![Wet tap against the dry with the LFO and after an onset, and the average response while sweeping](../measurements/basstide/targets.svg)](../measurements/basstide/targets.svg "Open the full-size plot")

Data: [`targets_wet_tap.csv`](../measurements/basstide/targets_wet_tap.csv) (`mode, input_dbfs, time_s, offset_samples`).

### Harmonics

[![Harmonic levels of 41 Hz, 110 Hz and 220 Hz sines at the defaults](../measurements/basstide/harmonics.svg)](../measurements/basstide/harmonics.svg "Open the full-size plot")

Data: [`harmonics.csv`](../measurements/basstide/harmonics.csv) (`f0_hz, harmonic, level_dbc`).

## What to tune by ear

Every value is chosen, and nothing has been listened to. The constants are in `src/basstide.dsp`.

1. Crossover (200 Hz): where the dry low band meets the flanged high band.
2. Glide (400 ms), and `glideHold` and `glideSmooth`: the shape and length of the note sweep.
3. `onsetRatio` (6 dB) and `levelRef` (−20 dBFS): what counts as a new note, and how hard you have to play for the full sweep.
4. `bumpNorm` (1.7): how far a strong note throws the sweep.
5. `zeroSamples` (96) and `lagMaxSec` (8 ms): how far the wet runs ahead of and behind the dry.
6. Feedback near ±90 %: whether the static comb on a held note is a welcome colour.

## Known limitations

- **Draft.** Not compiled or tested yet.
- **The note sweep only goes behind the dry.** In Follow mode the comb approaches zero from one side and doesn't cross it. Through-zero crossings come from the LFO.
- **The zero point is fixed in samples,** so at 96 kHz the wet can only run 1 ms ahead.
- **Mono only.**
