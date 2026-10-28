# Circuit notes: what BassEras borrows

BassEras is a **circuit-inspired** effect. These notes record what public sources say about the pedal it borrows from, the Tech 21 SansAmp Character Series VT Bass DI, and which parts of that BassEras keeps. "Tech 21", "SansAmp", "Character Series" and "VT Bass DI" appear here only to identify the reference pedal; the plugin carries none of that branding. What BassEras adds, and every value it chooses, is in the [design notes](design-notes.md).

No proprietary plugin, binary or firmware was inspected. Everything below comes from the sources listed at the end.

Confidence levels used throughout:

- **Documented**: stated by the manufacturer.
- **Reported**: stated by a third party (a forum trace, a review). It hasn't been checked against the pedal.
- **Inferred**: my own reasoning from the documented and reported facts.
- **Chosen**: a free modelling choice where no source gives a value.

The most important caveat: **no schematic of this pedal is public**, as far as I could find. Its clipping stages sit in a sealed module, and the community traces of the related guitar pedals in the same series [3] give a signal chain and some part values around the module, with question marks, but nothing inside it. So BassEras borrows the documented controls, the documented EQ and the reported order of the stages, and chooses the stages themselves. The schematic below is a standard analogue stand-in for that chain, not a trace.

---

## 1. Controls and interface (documented [1], [2])

| Control | Function | Confidence |
|---|---|---|
| LEVEL | Output level of both outputs | Documented [1] |
| BLEND | Mix of the direct signal and the preamp. At minimum the preamp is bypassed, "however, the Mid, Low, High and Level controls remain active." | Documented [1], [2] |
| DRIVE | "The overall amount of gain and overdrive, similar to when the output section of a tube amp is being pushed" | Documented [1] |
| CHARACTER | Sweeps through amp voicings of several eras. "In addition to modifying the frequency response, the Character control also influences the attack and drive characteristics." Below noon is a 1970s high-power stack, noon a 1960s studio flip-top combo, above noon "increases the gain and crunch", and full up gives distorted tones. | Documented [1] |
| LOW | ±12 dB from unity at noon, 125 Hz | Documented [1] |
| MID | ±12 dB from unity at noon, 1 kHz | Documented [1] |
| HIGH | ±12 dB from unity at noon, 3.2 kHz | Documented [1] |
| BITE switch | "A presence boost and subsonic filter." It "tightens up the sound when you are in distorted settings and adds definition to your notes when playing in clean settings." All eight of the manual's sample settings have it on. | Documented [1], [2] |

Other documented facts [1]:

- The speaker simulation is "tuned to match 10-inch American-style bass speakers", and designed for "a smooth, even response as would be achieved by a multiply-miked cabinet, without the peaks, valleys, and notches associated with single miking."
- "A hotter signal and a heavy hand will increase the gain structure and result in more overdrive", and the circuit "limits transient peaks for an even meter reading."
- The input is 1 MΩ. The pedal runs from a 9 V battery or supply, or from phantom power.

Not borrowed: the −20 dB XLR pad, the +10 dB switch on the 1/4" output, the parallel output, phantom power and the ground lift. These are output-stage features with no effect on the tone.

## 2. Topology

**Inferred from [1]:** the EQ follows the blend, because it stays active with Blend at minimum, when the preamp is bypassed. The speaker simulation is part of the preamp path ("an integral part of the SansAmp circuitry"), so the direct side of the blend is full-range.

**Reported [3]:** posters tracing the guitar pedals of the same series give this chain: an input stage; a pre-clipping EQ, which is the Character control, described as "a high gain (+ and - 15dB) variable midrange boost or cut"; the gain control; the sealed module with two gain stages, the second with "two back to back 3.3v silicon zener diodes in the feedback loop"; a "two stage high frequency rolloff or 'speaker simulator' circuit"; the output level; and active Baxandall-style bass, mid and treble stages. The bass pedal of the series is reported to use the same module type (CH34-4) as one of the guitar pedals.

**Inferred:** the bass DI keeps this chain, with the Bite switch's subsonic filter ahead of the clipping (it "tightens" distorted settings, which only makes sense if it reduces what reaches the clipper) and its presence boost after it.

```text
in -> buffer -+------------------------------------------------- direct --+
              |                                                            |
              +-> [Bite subsonic] -> Character EQ (mid +/-15 dB)           Blend
                  -> Drive -> module: gain stage 1 -> gain stage 2         |
                     (zeners in feedback) -> [Bite presence]               |
                  -> two-stage high-frequency roll-off (speaker sim) ------+
   -> Level -> Low / Mid / High (active, +/-12 dB) -> out
```

## 3. What BassEras keeps, and with what confidence

| Part | BassEras | Confidence |
|---|---|---|
| Control set | Level, Blend, Drive, Character, Low, Mid, High, Bite | Documented [1]. Bite is continuous here, and Cab Bypass is added (design notes) |
| EQ frequencies and range | 125 Hz, 1 kHz, 3.2 kHz, ±12 dB, flat at noon | Documented [1] |
| EQ shapes | Symmetric 2nd-order shelves (Q 0.707) and a peak (Q 0.7) | Chosen. The reported Baxandall stages [3] cut and boost symmetrically, which the shelves do too |
| EQ after the blend | Yes | Inferred from [1] |
| Character as a pre-clip mid boost or cut | ±15 dB | Range reported [3], frequency and law chosen |
| Character also adding gain above noon | Up to 12 dB | Behaviour documented [1], amount chosen |
| Two gain stages, the second clipping harder | Soft tanh, then a hard knee | Order reported [3], shapes chosen |
| Stage 2 clip level | ±3.1 V | Inferred: a TL07x-type op-amp on a 9 V supply swings to about 1.5 V from each rail, so about ±3.1 V about its bias (as for BassPreamp). The reported 3.3 V zeners plus a forward drop would only clip at about ±3.9 V, beyond the rails (open question 2) |
| Bite: subsonic high-pass before the clipping, presence peak after | 40 Hz, +6 dB at 2.5 kHz | Function documented [1], placement inferred, values chosen |
| Speaker sim: two-stage high-frequency roll-off, smooth | −3 dB at about 3.7 kHz, no peak | Roll-off reported [3], smoothness documented [1], corners chosen |

Every chosen value, with its intent, is in section 4 of the [design notes](design-notes.md).

## 4. The stages as drawn

The [schematic](../development/schematics.md) draws the chain BassEras implements as standard analogue stages: op-amp gain stages, Sallen-Key filters, graphic-EQ bands with simulated inductors, and a peak detector. Every part is chosen and outlined with a dashed rectangle, apart from the documented input impedance. Nothing in it is a trace of the pedal. It shows one way the DSP's chosen corners could be built, and its script (`tools/schematics/basseras.py`) checks each corner, gain and Q against the DSP constants. The sheets are numbered after this list.

![Root sheet: the block diagram, one hierarchical sheet per stage](../schematics/basseras/basseras.svg)

**Sheet 1, Supply and bias.** The 9 V supply and a half-supply bias rail VB for the op-amps (chosen).

![Sheet 1: Supply and bias](../schematics/basseras/basseras-1-supply-and-bias.svg)

**Sheet 2, Input buffer.** The documented 1 MΩ input [1], a 5 Hz coupling (the DSP's `fi.dcblockerat(5)`) and a unity-gain buffer. Its output feeds both the preamp path and the clean side of the Blend.

![Sheet 2: Input buffer](../schematics/basseras/basseras-2-input-buffer.svg)

**Sheet 3, Bite: subsonic filter.** A unity-gain Sallen-Key Butterworth high-pass whose two resistors are gangs of the Bite pot, so the corner glides from 10 Hz to 40 Hz (`biteHpLo`, `biteHpHi`).

![Sheet 3: Bite: subsonic filter](../schematics/basseras/basseras-3-bite-subsonic-filter.svg)

**Sheet 4, Character.** The pre-clip mid band (±15 dB, drawn at noon, 418 Hz, Q 0.7) and the extra gain of up to 12 dB above noon on a second gang (`charRange`, `charGainDb`).

![Sheet 4: Character](../schematics/basseras/basseras-4-character.svg)

**Sheet 5, Stage 1.** The Drive gain (0 to 30 dB, `driveMaxDb`), a soft clip at about two diode drops for the DSP's tanh at ±1.2 V (`v1`), and the 6 kHz inter-stage low-pass (`interLp`).

![Sheet 5: Stage 1](../schematics/basseras/basseras-5-stage-1.svg)

**Sheet 6, Stage 2 and bloom.** Gain 4 (`g2`), clipping at the op-amp's rails (about ±3.1 V, `railV`), a peak detector (20 ms attack, 150 ms release) whose output a Character gang feeds back as the bias bloom, and the 5 Hz DC block after it.

![Sheet 6: Stage 2 and bloom](../schematics/basseras/basseras-6-stage-2-and-bloom.svg)

**Sheet 7, Bite: presence boost.** A boost-only band, +6 dB at 2.5 kHz, Q 0.7 (`presF`, `presDb`, `presQ`).

![Sheet 7: Bite: presence boost](../schematics/basseras/basseras-7-bite-presence.svg)

**Sheet 8, Speaker sim.** Two Sallen-Key low-passes (4.5 kHz Q 0.707, 6 kHz Q 0.6), a 30 Hz high-pass, and the Cab Bypass switch, which the DSP crossfades.

![Sheet 8: Speaker sim](../schematics/basseras/basseras-8-speaker-sim.svg)

**Sheet 9, Blend.** A linear crossfade between the clean path and the preamp path, with the preamp path's trim (`drvTrim`).

![Sheet 9: Blend](../schematics/basseras/basseras-9-blend.svg)

**Sheet 10, Low, Mid and High.** Boost and cut bands set to the documented 125 Hz, 1 kHz and 3.2 kHz, ±12 dB [1]. The shelves are first-order here; the DSP's are second-order.

![Sheet 10: Low, Mid and High](../schematics/basseras/basseras-10-low-mid-high.svg)

**Sheet 11, Level.** A volume pot and a fixed +12 dB stage for the DSP's −40 to +12 dB Level.

![Sheet 11: Level](../schematics/basseras/basseras-11-level.svg)

## Sources

1. Tech 21, *SansAmp Character Series VT Bass DI owner's manual*, rev. 12.20. <https://www.tech21nyc.com/t21manuals/VT_DI_OM_v6.pdf>
2. Tech 21, *VT Bass DI* product page. <https://www.tech21nyc.com/products/sansamp-2/vtbass-di/>
3. freestompboxes.org, "Tech21 Character Series" thread (community traces of the series' guitar pedals, with component tables). <https://www.freestompboxes.org/viewtopic.php?t=6571>. The thread refused automated access while these notes were written, so what is quoted here comes from search-engine excerpts of it; the confidence is low.
4. PedalPCB forum, "Tech21 VTDI" thread, which notes that the pedal is based on the Character Series circuit with a DI added, not on the Bass Driver DI. <https://forum.pedalpcb.com/threads/tech21-vtdi.19367/>

## Open questions

1. What is the Character control's actual circuit: which direction does it boost and cut, at what frequency, and does the frequency move? BassEras assumes a cut at the low end of the travel and a boost at the high end, with a moving centre.
2. Do the zeners or the op-amp rails set stage 2's clip level? On a 9 V supply the rails come first, unless the module runs from a higher internal rail.
3. What are the Bite filter's corner frequency and order, and the presence boost's frequency and gain?
4. What does the speaker simulation's response look like in the pedal? Only "two stage" and "smooth" are known.
5. Does the pedal's Blend crossfade, or add the direct signal as BassPreamp's does?
