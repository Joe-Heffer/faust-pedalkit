# Design notes: Mid-Life Crisis

!!! note "Status: concept sketch"
    This is the first sketch of a proposed effect. There is no DSP, no tests and no effect page yet. It sets out the idea, the blocks, the constants and the targets so they can be argued over before any code is written. Every value below is a proposal.

Mid-Life Crisis is a **circuit-inspired** high-gain distortion for bass. The borrowed part is the structure of a well-known 1990s high-gain guitar pedal, the Boss MT-2 Metal Zone: two clipping stages in series, with filtering before and between them, followed by an active three-band EQ with a sweepable mid. The manufacturer and product names appear here only to identify the reference hardware. The plugin will carry none of that branding.

The name is the joke and the design. The reference pedal is known for one sound: mids scooped out, lows and highs boosted, Dist near full. On a bass that setting removes the part of the spectrum that lets the instrument be heard in a band. This effect is a scoop pedal that has a crisis about its mids. The scoop is still there, and the same control goes the other way into a mid boost.

!!! warning "Sources not yet read"
    This sketch was written in a session whose network policy blocked the reference pages ([1], [2], [3] could not be fetched). The facts about the reference pedal below come from search-engine summaries of those pages and are marked **reported (summary only)**. Before any DSP is written, the pages must be read directly and circuit notes (`docs/midlifecrisis/circuit-notes.md`) written for the borrowed part, with a schematic, as `AGENTS.md` requires. Nothing here is taken from any plugin, binary or firmware.

## 1. The idea

A high-gain guitar distortion on a bass has three problems:

* The fundamental (31 Hz to 98 Hz on the open strings) goes through the clipper with everything else. Clipped low notes intermodulate into mud and the low end loses its weight.
* The guitar voicing removes low end before the clipper, so what comes out is thin.
* The signature scooped EQ setting removes 300 Hz to 1 kHz, which on bass is where the note's identity sits.

What a player gets that the reference pedal does not give them:

* **The low end stays clean.** The signal is split at a Crossover. Only the upper band goes through the two clipping stages. The low band bypasses them and comes back at Low Blend, time-aligned with the driven band. The same approach as [BassGrit](../bassgrit/index.md), taken to far higher gain.
* **A mid sweep tuned for bass.** The reference's mid control is reported as sweeping 200 Hz to 5 kHz [1]. Here it sweeps 100 Hz to 2 kHz, where the bass's body and growl are.
* **Crisis**, one control for the whole EQ curve. At one end it is the classic scoop (mids down, lows and highs up). At the centre it is flat. At the other end it is a mid-forward growl with the extremes trimmed. A player can still move each band separately.

Measurable description:

* A 41 Hz fundamental passes within 3 dB of its clean level at full Dist, at the default Crossover and Low Blend 100.
* The upper band is driven hard: at Dist 100, 1 kHz small-signal gain is above 50 dB and a −20 dBFS 220 Hz tone is near square in the upper band.
* Crisis at its two ends gives a mid notch and a mid peak of equal size, centred on Freq.

## 2. Prior art and inspirations

1. Boss, MT-2 Metal Zone product page, <https://www.boss.info/NZ/products/mt-2>. Reported (summary only): two gain stages in series, the first mid-focused feeding a more aggressive second; seven stages of filtering before and after the distortion; a three-band active EQ with up to 15 dB boost and cut per band and a mid centre variable from 200 Hz to 5 kHz.
2. Electric Druid, “Boss MT-2 Metal Zone pedal analysis”, <https://electricdruid.net/boss-mt-2-metal-zone-pedal-analysis/>. Reported (summary only): a block-by-block analysis of the schematic that describes the tone control as unusually sophisticated for a mass-market pedal. Not yet read; it is the main source for the circuit notes.
3. Mirosol, “Boss MT-2 Metal Zone”, <https://mirosol.kapsi.fi/2013/12/boss-mt-2-metal-zone/>. Reported (summary only): a schematic review that notes several gyrators in the EQ alongside the gain stages.
4. [BassGrit](../bassgrit/design-notes.md): a 4th-order Linkwitz-Riley band split that keeps the low band out of a hard clipper. Reused here.
5. [MidHump](../midhump/design-notes.md) and [BassDrive](../bassdrive/index.md): clean paths delayed to match an oversampled path.

Borrowed from the reference: two clipping stages in series with a filter between them, and a three-band EQ with a semi-parametric mid after them. New: the band split, the bass mid range, the Crisis macro and the clean low band.

## 3. Block diagram

```text
in → DC blocker (5 Hz) → LR4 split at Crossover
       ├─ low band ──────────────── delay 2 × os4Latency ─────────── × Low Blend ─┐
       └─ high band → pre-emphasis → [stage 1: soft clip] → inter-stage filter      │
                        → [stage 2: hard clip] → post low-pass ────────────────────┤
                                                                                   ↓
                                    sum → EQ (Low shelf, Mid peak at Freq, High shelf)
                                        → Level → pk.safety(0.989) → out
```

The square brackets are memoryless shapers, each in its own `pk.oversample4`. They have a filter between them, so they cannot share one oversampler. That costs 2 × 32 = 64 samples of latency, within the 128-sample budget, and the low band is delayed by the same named constant.

| Block | New or reused |
|---|---|
| DC blocker (5 Hz) | Reused (`fi.dcblockerat`) |
| Linkwitz-Riley 4th-order split | Reused from BassGrit. A second effect needs it, so it should move into `pedalkit.lib` as part of this work |
| Pre-emphasis (mid-focused band-pass before stage 1) | New, standard `fi` filters |
| Stage 1 soft clipper | Reused (`pk.softSat`) inside `pk.oversample4` |
| Inter-stage filter | New, standard `fi` filters |
| Stage 2 hard clipper | Reused (`pk.kneeClip`) inside `pk.oversample4` |
| Post low-pass (fizz control) | New, `fi.lowpass` |
| Clean low band, delayed by 2 × `pk.os4Latency` | Same pattern as BassGrit |
| Low and High shelves | Reused (`pk.lowShelf2`, `pk.highShelf2`) |
| Mid peaking filter | New. A constant-Q peak with cut mirroring boost; a candidate for `pedalkit.lib` |
| Crisis macro | New in this file |
| Output limiter | Reused (`pk.safety`) |

## 4. Proposed controls

| Label | Unit | Range | Default | Notes |
|---|---|---|---|---|
| Dist | % | 0 to 100 | 60 | Gain into both stages, log law |
| Low | dB | −15 to +15 | 0 | Low shelf |
| Mid | dB | −15 to +15 | 0 | Mid peak |
| Freq | Hz | 100 to 2000 | 500 | Mid centre, log law |
| High | dB | −15 to +15 | 0 | High shelf |
| Crisis | % | −100 to +100 | 0 | Macro added to Low, Mid and High; see section 5 |
| Crossover | Hz | 60 to 400 | 150 | Band split |
| Low Blend | % | 0 to 100 | 100 | Clean low band level |
| Level | dB | −40 to +12 | 0 | Output |

## 5. Constants

All values are **chosen** unless marked otherwise. The circuit values of the reference, once read, will go in the circuit notes.

| Constant | Value | Confidence | Intent |
|---|---|---|---|
| EQ range | ±15 dB per band | Reported (summary only) [1] | The reference's range, kept. |
| Mid sweep | 100 Hz to 2 kHz | Chosen | The reference's 200 Hz to 5 kHz [1] moved down about an octave and a bit for bass. 100 Hz reaches the low-mid thump, 2 kHz the string clank. |
| Mid Q | 0.9 | Chosen | Wide enough for a scoop to be obvious, narrow enough that Freq audibly moves it. The reference's Q is not yet known; the circuit notes should say. |
| Shelf corners | Low 100 Hz, High 3 kHz | Chosen | Outside the default mid sweep. To be compared with the reference's corners once [2] is read. |
| Crisis law | Mid = Crisis × 15 dB; Low and High = −Crisis × 9 dB | Chosen | −100 is the classic scoop (Mid −15, Low and High +9), +100 is the crisis (Mid +15, Low and High −9). Added to the separate bands and clamped to ±15 dB. |
| Crossover range | 60 to 400 Hz, default 150 Hz | Chosen | A little higher than BassGrit's 120 Hz default because the gain is far higher, so the upper band's lower skirt needs to stay further from the fundamentals. |
| Split slope | 4th-order Linkwitz-Riley | Chosen | As in BassGrit: flat sum, 24 dB/octave. |
| Pre-emphasis | band-pass, 300 Hz to 3 kHz, about 12 dB | Chosen | Stands in for the reference's “mid-focused” first stage [1] until its filters are known. |
| Stage 1 shaper | `pk.softSat`, knee 0.6 | Chosen | A soft first stage so that light playing cleans up. |
| Stage 1 gain | 0 to 30 dB | Chosen | Split of the total gain between the stages, to tune by ear. |
| Inter-stage filter | high-pass 200 Hz, low-pass 6 kHz | Chosen | Keeps the second stage from re-clipping the first stage's lowest intermodulation products and its fizz. |
| Stage 2 shaper | `pk.kneeClip`, level 0.6, hardness 4 | Chosen | The hard, square character the reference is known for. |
| Stage 2 gain | 0 to 30 dB | Chosen | As stage 1. |
| Post low-pass | 5 kHz | Chosen | Removes the harshest fizz above the bass's useful range. |
| Latency | 64 samples (2 × `pk.os4Latency`) | Inferred | Two oversamplers with a filter between them. |

## 6. Measurable targets

To be checked in `tests/midlifecrisis/test_targets.py` once the DSP exists.

1. With Dist 0, all EQ at 0, Crisis 0 and Low Blend 100, the response is flat within 1 dB from 30 Hz to 8 kHz, so the split sums flat and the two paths are time-aligned.
2. At Dist 100, Crossover 150 Hz, Low Blend 100, a −12 dBFS 41 Hz tone has at least 20 dB less THD than at Crossover 60 Hz.
3. At Dist 100, 1 kHz small-signal gain is above 50 dB.
4. The Mid peak is centred on Freq within a third of an octave at 100 Hz, 500 Hz and 2 kHz, and reaches ±15 dB within 0.5 dB.
5. Crisis −100 and +100 give responses that mirror each other within 1 dB in dB terms (cut mirrors boost).
6. The distortion is odd-order: even/odd harmonic ratio below −30 dB at Dist 100.
7. 4x oversampling lowers the worst alias by at least 20 dB against a 1x build for a 441 Hz tone at Dist 100. A near-square wave aliases at higher pitches whatever the oversampling (see BassGrit target 10), so the limit above 1 kHz is to be set after measuring.
8. Reported latency is 64 samples and matches the measured delay (`tests/common/test_latency.py`).

## 7. Dynamics and feel

The aim is a high-gain sound that still answers to the right hand, which most high-gain designs do not.

* **Cleanup curve.** Stage 1 is soft, so at Dist 50, H3 should rise steadily over at least 20 dB of input level before stage 2 squares the wave off, rather than jumping from clean to square within 6 dB. Checked with `harmonic_trajectory`.
* **Attack against sustain.** At high Dist, the attack and the sustain should both be fully clipped, so the sound sustains like the reference. No envelope-driven behaviour is planned for the first version.
* **A possible sag.** A slow headroom envelope on stage 2 (the pattern in [Designing for feel](../development/designing-for-feel.md)) could make the gain compress on loud passages. Left out of the first version; see open questions.

## 8. Open questions

Only listening, or the sources not yet read, can answer these.

* What do the reference's filter stages [2] actually do, and how much of its character is the filtering against the clipping? This decides whether the pre-emphasis and inter-stage filter above stay as chosen stand-ins or become modelled stages.
* Is 150 Hz the right default Crossover at this much gain, and does a five-string low B need lower?
* Is the Crisis law (±15 dB on Mid against ∓9 dB on the shelves) the right curve, or should it also move Freq?
* Does Crisis −100 on bass sound like the joke it is meant to be, or just thin?
* How should the gain be split between the stages? This is the main tuning parameter for the character.
* Would a sag on stage 2 help the feel, or make the sound less tight?
* Will the near-square upper band alias audibly above about 500 Hz at full Dist, and is an 8x oversampler for stage 2 worth the latency?
* `declare name`: “Mid-Life Crisis” with spaces and a hyphen, or `MidLifeCrisis` to match the other effects?
