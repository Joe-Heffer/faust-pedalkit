# MidHump

A mid-hump overdrive. Mids are driven into soft diode clipping while bass passes at unity gain, which keeps the low end tight. An optional clean Blend, which the original circuit does not have, brings back the full range.

!!! warning "Untested first draft"
    This page describes the design. The plugin has not yet been compiled or measured, so there is no measured behaviour section. It is added once `make test FX=midhump` has run.

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
| Tone | 0 to 100 % | 50 % | Treble shelf after the 723 Hz low-pass, about 13 dB of range |
| Level | −40 to +12 dB | 0 dB | Output level |
| Blend | 0 to 100 % | 0 % | Adds a full-range clean signal. 0 is the circuit as published. |

Every control is smoothed. The plugin also has a read-only *Latency* output for the host.

## Signal path

```text
in → input high-pass (15.6 Hz)
   ├─ clean:  delay 32 samples → × Blend × 0.5 ──────────────────────────┐
   └─ clipping stage: input + 4x oversampled diode clip of               │
        (720 Hz high-pass → feedback low-pass → gain 11.9 to 118)        │
      → 723 Hz low-pass → Tone shelf → DC blocker (5 Hz) ────────────────┤
→ sum → Level → safety limiter (≤ −0.1 dBFS) → out
```

## What to tune by ear

These values are chosen or inferred, and nothing has been listened to. The constants are in `src/midhump.dsp`.

1. `Vd` (0.6 V): the diode knee level. Lower gives more compression and earlier clipping.
2. The Drive law (`Rd`): where in the travel the gain rises.
3. `cleanTrim` (0.5): the size of the Blend path.
4. `fcZero` and `fcShelf`: the Tone shelf, which is a stand-in for the real tone network.
5. The input level convention: 0 dBFS is treated as 1 V at the input.

## Known limitations

* **Not a circuit simulation.** The diodes are a static soft clipper, and the feedback low-pass sits before them instead of acting on the clipped signal.
* **Tone is behavioural.** See section 7 of the [circuit notes](circuit-notes.md).
* **Input and output buffers and the op-amp's own limits are not modelled.**
* **Mono only.**

MidHump is an independent design built from public information. It is not affiliated with, or endorsed by, any pedal manufacturer.
