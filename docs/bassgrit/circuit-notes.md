# Circuit notes: the op-amp hard-clipping distortion

These notes record what public sources say about the classic op-amp distortion pedal that BassGrit borrows from (the Pro Co RAT), and how BassGrit turns that into DSP. The manufacturer and product names appear here only to identify the reference hardware. The plugin carries none of that branding.

No proprietary plugin or firmware was inspected. Everything below comes from the sources at the end, plus standard circuit analysis.

!!! warning "Status of these notes"
    Written in a session where the primary analysis page (ElectroSmash [1]) could not be fetched: the connection failed. The values below come from search-engine summaries of [1] to [3], and from the author's recall of the standard schematic. **No value has been checked against a schematic.** Each is marked, and everything marked **reported** from a summary or **inferred** from recall must be checked against the primary sources before the effect is released.

Confidence levels used throughout:

- **Documented**: stated by the manufacturer, a datasheet or a cited paper.
- **Reported**: stated by one or more third parties (an analysis, a forum post or a measurement). Where only a summary was seen, the text says so.
- **Inferred**: my own reasoning from the reported facts, or recall that no source in hand confirms.
- **Chosen**: a free modelling choice where no source gives a value.

This is the borrowed part only. The departures (the band split, the filter range, the output trim) are in the [design notes](design-notes.md).

---

## 1. Controls and interface

The pedal has three controls: Distortion (the gain), Filter (a low-pass that darkens as it is turned up) and Volume [1]. BassGrit keeps the first two and adds Low Blend and Crossover (see the [design notes](design-notes.md)).

## 2. Block diagram

```text
in → input coupling → op-amp gain stage → series resistor + diode pair to ground → Filter → output buffer
```

The input and output buffers are not modelled (**chosen**): they match impedances, which a digital model has no use for.

## 3. Input coupling

**Reported [1] (summary):** a 22 nF coupling capacitor and a 1 MΩ pull-down give a high-pass at

  f = 1 / (2π · 1 MΩ · 22 nF) ≈ **7.2 Hz**

BassGrit replaces this with a 5 Hz DC blocker (`fi.dcblockerat(5)`, **chosen**: a bass note at 31 Hz must pass at full level, and the difference is 0.1 dB).

## 4. Gain stage

**Reported [1], [3]:** a non-inverting op-amp stage with gain

  G = 1 + Zf / Zg

- The grounded side Zg is two RC legs in parallel: **47 Ω + 2.2 µF** and **560 Ω + 4.7 µF** (component values reported [1]).
- The feedback side Zf is the Distortion pot (**100 kΩ**, **inferred**: recall) in parallel with **100 pF** (**inferred**: recall).

Each leg is a first-order high-pass: its admittance is `(1/R) · s/(s + ω)`. So

  G(s) = 1 + Rf · [ HP_A(s) / 47 Ω + HP_B(s) / 560 Ω ] · LP(s)

- HP_A corner: 1 / (2π · 47 Ω · 2.2 µF) ≈ **1.54 kHz**. HP_B corner: 1 / (2π · 560 Ω · 4.7 µF) ≈ **60.5 Hz**. A forum estimate gives "roughly 60 Hz and 1500 Hz" [3] (**reported**).
- The gain at high frequency is **1 + 100 kΩ / (47 Ω ‖ 560 Ω) ≈ 2300 (67 dB)** at full Distortion, falling to 1 at Distortion 0.
- At full Distortion the second leg alone gives 1 + 100 kΩ / 560 Ω ≈ 180 (45 dB) between 60 Hz and 1.5 kHz, and the first leg adds above that (**derived** from the reported values).

**Gain-bandwidth limit.** The pedal's op-amp is an LM308 (**reported** [1], [4]) with a small compensation capacitor, and its gain-bandwidth product sets the bandwidth at high gain: closed-loop bandwidth ≈ GBW / G. [4] says this drives the high-frequency roll-off at high Distortion. BassGrit uses **GBW = 1 MHz** (**inferred**: order of magnitude only; the datasheet was not read, and the real part varies from sample to sample [4]). That gives a closed-loop pole of about 430 Hz at full Distortion and about 4.8 kHz at noon.

The feedback capacitor adds a second low-pass at 1 / (2π · Rf · 100 pF): 16 kHz at full Distortion.

**Chosen: Distortion pot law.** No source gave the taper. BassGrit uses a logarithmic law, `Rf = 100 kΩ · (10^(2·Distortion) − 1) / 99`, about 9 % of the pot at noon. It is the same law as MidHump's Drive and BassDrive's Gain.

**Model structure.** As in MidHump, the op-amp output is the input plus a branch: `out = in + (Zf / Zg) · in`, the branch being the two scaled high-passes followed by the two low-passes. The op-amp's own rail limits (the output stage of a 9 V supply) are not modelled (**chosen**: see [open questions](#open-questions)).

## 5. The diodes

**Reported [1]:** two 1N914 (silicon switching) diodes, antiparallel, from the op-amp output to ground through a series resistor of **1 kΩ** (the resistor is **inferred**: recall). Unlike a diode-in-feedback overdrive, these clip to ground, after the gain stage, so the clipped signal is not added to the input. At high Distortion the output is close to a square wave of about ±0.6 V.

**Chosen model:** a memoryless `pk.kneeClip(0.6, 4)` run at 4x oversampling. The limit **0.6 V** is **inferred** from the forward voltage of silicon diodes (about 0.5 V to 0.7 V). The knee hardness 4 is **chosen**: harder than a tanh and softer than a clamp. Changing it from 1.5 to 4 moves the worst alias by only 3 dB (the clipper input is far above threshold), so the choice matters for tone, not for aliasing.

The 1 kΩ series resistor and the diodes also load the Filter's source impedance; its 1.5 kΩ is far larger, and the interaction is not modelled (**chosen**).

## 6. Filter

**Reported [1] (summary):** a first-order passive low-pass: a **1.5 kΩ** resistor in series with a **100 kΩ** pot (pot value **inferred**: recall), into **3.3 nF** to ground. The corner is

  f = 1 / (2π · (1.5 kΩ + Rpot) · 3.3 nF)

which runs from **32.1 kHz** (pot at 0) down to **475 Hz** (pot at 100 kΩ) (**derived**). Turning the knob up darkens the sound. BassGrit keeps the structure and the law and changes the capacitor to 4.7 nF (see the [design notes](design-notes.md)), giving 22.6 kHz to 334 Hz.

## 7. Level and calibration

**Chosen:** 1.0 digital full scale is treated as 1 V peak at the circuit input. The 0.6 V clip then sits at −4.4 dBFS, and an `outTrim` of 1.2 restores some of the level (see the design notes). The pedal's volume stage is replaced by a plain gain in dB.

---

## Sources

1. ElectroSmash, [ProCo RAT analysis](https://www.electrosmash.com/proco-rat). Not fetched in the session that wrote these notes; values from the parts list and summary in search results.
2. PedalPCB, [Muroidea (RAT) build thread](https://forum.pedalpcb.com/threads/muroidea-proco-rat.12237/). Input coupling, filter and the substitute op-amps.
3. DIYStompboxes, [Proco Rat Redesign](https://diystompboxes.com/smfforum/index.php?msg=797495). The two grounded legs and their approximate corners.
4. PedalPCB, [forum post on the LM308's gain-bandwidth product](https://forum.pedalpcb.com/goto/post?id=387002).
5. Wikipedia, [Pro Co RAT](https://en.wikipedia.org/wiki/Pro_Co_RAT). History only.

## Open questions

1. Check every value above against a schematic and the ElectroSmash analysis. In particular the 100 kΩ pot, the 100 pF capacitor, the 1 kΩ series resistor, the 30 pF compensation capacitor and the LM308's GBW at that capacitance, and the supply voltage.
2. Does the LM308's output swing (slew and rail limits) add clipping before the diodes at high Distortion? The model has none.
3. Should the diodes be modelled with the Shockley equation rather than a static knee? the [MidHump circuit notes](../midhump/circuit-notes.md) cite Yeh's method for it.
