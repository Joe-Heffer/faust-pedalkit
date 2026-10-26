# Circuit notes: the mid-hump overdrive

These notes record what public sources say about the classic green mid-hump overdrive pedals (the Ibanez TS808 and TS9 family), and how MidHump turns that into DSP. The manufacturer and product names appear here only to identify the reference hardware. The plugin carries none of that branding.

No proprietary plugin or firmware was inspected. Everything below comes from the sources at the end, plus standard circuit analysis.

!!! warning "Status of these notes"
    The first draft was written in a session that could not open the primary sources (ElectroSmash, GeoFex, the Yeh papers): the network policy blocked them. Component values come from search-engine summaries of those pages, from the figures quoted in issue #31, and from the author's recall of the standard schematic. Each value is marked below. Check every **reported** and **inferred** value against the primary sources before the effect is released.

Confidence levels used throughout:

* **Documented**: stated by the manufacturer, a datasheet or a cited paper.
* **Reported**: stated by one or more third parties (an analysis, a forum post or a measurement), and seen in this session only through a summary.
* **Inferred**: my own reasoning from the reported facts.
* **Chosen**: a free modelling choice where no source gives a value.

---

## 1. Controls and interface

The pedal has three controls: Drive (distortion), Tone and Level (issue #31, sources [1] and [2]). MidHump adds a fourth, Blend, which the pedal does not have (see the [design notes](design-notes.md)). At Blend 0 the plugin is the model described here.

## 2. Block diagram

```text
in → input buffer → clipping stage ┬→ 723 Hz passive low-pass → active tone stage → Level → output buffer
                                   └ op-amp with diodes in the feedback loop
```

Input and output buffers are not modelled (**chosen**). They are emitter followers whose job is impedance matching, so a digital model has no use for them.

## 3. Input coupling

**Inferred:** a 20 nF coupling capacitor into a 510 kΩ bias resistor gives a high-pass at

  f = 1 / (2π · 510 kΩ · 20 nF) ≈ **15.6 Hz**

Only the 510 kΩ value was seen in a summary, as a bill-of-materials entry. The capacitor value is recalled from the standard schematic. The effect on bass is small (−0.4 dB at 41 Hz). It is the `fcIn` constant in `src/midhump.dsp`.

## 4. Clipping stage

**Reported [1][2]:** a non-inverting op-amp stage. The gain is

  G = 1 + Zf / Zg

* The grounded leg Zg is R4 = 4.7 kΩ in series with C3 = 47 nF.
* The feedback impedance Zf is R6 = 51 kΩ plus the Drive pot (500 kΩ) in series, in parallel with C4 = 51 pF and two antiparallel silicon diodes.

Because Zg contains a capacitor, the gain depends on frequency:

  G(s) = 1 + (Rf / R4) · HP(s) · LP(s)

* HP is a first-order high-pass at 1 / (2π · R4 · C3) ≈ **720 Hz** (reported [2]).
* LP is a first-order low-pass at 1 / (2π · Rf · C4). It is 61 kHz at Drive 0 and about 5.7 kHz at Drive 100 (both reported [1]).
* The gain range is **1 + 51 kΩ / 4.7 kΩ ≈ 11.9 (21.5 dB)** to **1 + 551 kΩ / 4.7 kΩ ≈ 118 (41.5 dB)** (reported [1]).

Below 720 Hz the second term vanishes, so the stage passes bass at unity gain and amplifies mids. The output is always the input plus the clipped branch. The sum is the reason the pedal never goes fully square, and the reason for the hump.

**Chosen: Drive pot law.** No source gave the taper. MidHump uses a logarithmic (audio) law, `Rd = 500 kΩ · (10^(2·Drive) − 1) / 99`, about 9 % of the pot at noon. This is the same law as BassDrive's gain pot. It puts the noon gain at 1 + (51 + 45) kΩ / 4.7 kΩ ≈ 21 (26.7 dB).

## 5. The diodes

**Reported [3]:** two silicon diodes in antiparallel in the feedback loop, which limit the voltage across Zf. Yeh models them with the Shockley equation and solves the circuit numerically.

**Chosen model:** the diodes limit the **feedback branch voltage** (Zf's drive, Vout − Vin). The model is a memoryless `pk.softSat(Vd)` with Vd = 0.6 V, run at 4x oversampling. The 720 Hz high-pass and the C4 low-pass sit outside the oversampler. This follows the simplification in [3] and [4], where the capacitor and diodes share one node.

* **0.6 V** is **inferred** from the usual conduction range of small-signal silicon diodes (0.5 V to 0.7 V). The knee is softer than a hard clip and harder than a real exponential diode. The knee shape is **chosen**.
* The clipper is symmetric, so the distortion is odd-order (reported [1]).

**Known approximation:** in the circuit, C4 and the diodes act together on the feedback node, so the low-pass acts on the clipped signal as well. In this model the low-pass comes before the clipper. At high Drive that leaves more high-frequency energy in the clipped waveform than the pedal has, and the 723 Hz passive filter that follows hides most of it.

## 6. Passive low-pass

**Reported [1]:** R7 = 1 kΩ and C5 = 220 nF form a first-order low-pass at **723 Hz** after the clipping stage. It removes the harsh upper harmonics. MidHump uses `fi.lowpass(1, 723)`.

## 7. Tone stage

**Reported [1][5]:**

* The active tone stage boosts treble to compensate for the passive low-pass above. At full treble the response is roughly levelled; at full bass the 20 dB/decade slope of the passive filter remains.
* A 220 Ω resistor in series with a 220 nF capacitor is part of the network. Above its corner of 1 / (2π · 220 Ω · 220 nF) ≈ **3.29 kHz** the pair behaves like the 220 Ω alone.

**Not established:** I could not read a complete netlist for the tone stage, and the two accounts I saw disagree on whether the 220 Ω network makes a boost or a cut. So MidHump does **not** solve the pot network. It uses a first-order shelf whose corners are the two reported frequencies:

  H(s) = (1 + s / ωz) / (1 + s / ωp), with fp = 3.29 kHz and fz = fp · (723 Hz / fp)^Tone

* At Tone 0, fz = fp and H = 1. Only the 723 Hz low-pass remains.
* At Tone 100, fz = 723 Hz. The zero cancels the passive pole, so the stage after the clipper is flat up to 3.29 kHz and then falls at 20 dB/decade.
* In between, the zero moves logarithmically. The treble boost over the whole range is 20 · log10(3.29 kHz / 723 Hz) ≈ **13.2 dB**.

This is **chosen** (the law) and **inferred** (the corners). It matches the qualitative descriptions, but it is not a circuit solution. Replacing it with the real network is the first item under [open questions](#open-questions).

## 8. Level and calibration

**Chosen:** Level is a plain gain in dB (−40 dB to +12 dB, default 0 dB), where the pedal has a passive volume pot and an output buffer. 1.0 digital full scale is treated as 1 V peak at the circuit input. At −12 dBFS the signal is 0.25 V peak, a plausible guitar level.

## 9. Summary of constants

| Constant | Value | Confidence |
|---|---|---|
| `fcIn` | 15.6 Hz | Inferred |
| `R4`, `C3` (720 Hz) | 4.7 kΩ, 47 nF | Reported |
| `R6`, `Rpot` | 51 kΩ, 500 kΩ | Reported |
| Drive law | log, ≈ 9 % at noon | Chosen |
| `C4` | 51 pF | Reported |
| `Vd` | 0.6 V | Inferred (knee shape chosen) |
| Passive low-pass | 723 Hz | Reported |
| Shelf corners | 723 Hz, 3.29 kHz | Inferred |
| Shelf law | log-interpolated zero | Chosen |
| Level range | −40 to +12 dB | Chosen |

---

## Sources

1. ElectroSmash, *Tube Screamer Circuit Analysis*: <https://www.electrosmash.com/tube-screamer-analysis>. Read through search summaries and mirrors only, not the original page.
2. R. G. Keen, *The Technology of the Tube Screamer*, Geofex: <http://www.geofex.com/Article_Folders/TStech/tsxtech.htm>. Read through search summaries only.
3. D. T. Yeh, J. Abel and J. O. Smith, *Simulation of the diode limiter in guitar distortion circuits by numerical solution of ordinary differential equations*, DAFx-07: <https://www.dafx.de/paper-archive/2007/Papers/p197.pdf>. Not read in this session.
4. D. T. Yeh, *Digital Implementation of Musical Distortion Circuits by Analysis and Simulation*, PhD thesis, CCRMA, Stanford, 2009: <https://ccrma.stanford.edu/~dtyeh/papers/DavidYehThesissinglesided.pdf>. Not read in this session.
5. ElectroSmash, *JRC4558 analysis*, for the op-amp choice: <https://www.electrosmash.com/jrc4558-analysis/pedals/distortion/jrc4558-analysis.html>. Not read in this session. The op-amp is modelled as ideal.
6. m0xpd, *Shack Nasties: Analysis of the Tube Screamer* (tone stage as a first-order shelf with a 220 nF complication): <https://m0xpd.blogspot.com/2012/11/analysis-of-tube-screamer.html>. Read through a search summary only.

## Open questions

* The tone stage netlist: which nodes R8, C6, the 20 kΩ pot and the 1 kΩ resistors connect to, and the resulting transfer function at each pot position. This replaces the shelf in section 7.
* The input coupling capacitor, and the 10 kΩ and 1 µF values in the buffer.
* Whether to move the C4 low-pass after the clipper, as in the circuit, at the cost of a filter inside the oversampled path.
* The diode knee. Yeh's numerical solution would settle the shape of the soft clipper.
* How the Drive pot is tapered in the pedals people play. A linear pot would change every noon figure above.
