# Design notes: BassEras

BassEras is a **circuit-inspired** effect. The borrowed part, described in the [circuit notes](circuit-notes.md), is the control set and signal chain of a bass preamp/DI pedal whose Character knob sweeps through amp voicings of different eras. No schematic of that pedal is public, so the stages themselves are chosen here, and so are their values. The departures are a Character control that also changes how a note attacks, a continuous Bite, and Cab Bypass.

## 1. The idea

Most preamps make the player set gain, EQ and feel separately. The reference pedal's manual describes one knob, Character, that does all three together: it "modifies the frequency response" and "also influences the attack and drive characteristics". BassEras makes that knob the centre of the design, and makes each thing it does explicit and measurable:

- **Below noon:** a scooped, deep voicing. A cut of up to 15 dB in the low mids before the clipping, centred near 250 Hz, keeps a big-stack low end without mud.
- **At noon:** flat and warm. No pre-clip EQ, only the soft first stage and the speaker sim.
- **Above noon:** pushed and crunchy. A boost of up to 15 dB in the upper mids, centred near 700 Hz, up to 12 dB more gain, and a **bias bloom**: a hard note pushes the second clipping stage off centre, so the note's body gains second harmonic a few tens of milliseconds after the attack, and loses it again as the note fades.

What a player gets that the pedal does not give them: the attack behaviour is a defined, repeatable effect of the knob rather than a side effect of the circuit; the Bite filter is a continuous amount instead of a switch; and the speaker sim can be bypassed for an external cabinet or impulse response.

## 2. Prior art

1. The reference pedal: [circuit notes](circuit-notes.md), sources 1 to 4.
2. [BassPreamp](../basspreamp/index.md) models the same maker's other bass preamp/DI. BassEras shares its pattern of a driven path, a clean path and an EQ after the blend, but has a different control set, different stages, and none of its traced values.
3. The bias shift is [MidHump](../midhump/index.md)'s Bloom, which uses `pk.biasShift` and `pk.biased` the same way. Here it is tied to Character rather than being a control of its own, and it sits on the second of two clipping stages (section 6 says why).

## 3. Blocks

| Block | New or reused |
|---|---|
| DC blocker (5 Hz) | Reused (`fi.dcblockerat`) |
| Bite subsonic high-pass, gliding 10 Hz to 40 Hz | New in this file (a 2nd-order section from `pk.tf2a`) |
| Character pre-clip EQ, gliding centre | Reused (`fi.peak_eq_cq`), with a new control law |
| Stage 1: gain and soft clip | Reused (`pk.softSat` in `pk.oversample4`) |
| Inter-stage low-pass | Reused (`fi.lowpass`) |
| Stage 2: gain and rail clip with the bias bloom | Reused (`pk.kneeClip`, `pk.biased`, `pk.biasShift` in `pk.oversample4c`) |
| Bite presence peak | Reused (`fi.peak_eq_cq`) |
| Speaker sim | New in this file (three 2nd-order sections from `pk.tf2a`) |
| Cab Bypass crossfade, Blend crossfade | Reused (`si.interpolate`), as in BassPreamp |
| Low and High shelves | **New in `pedalkit.lib`**: `pk.lowShelf2` and `pk.highShelf2`, 2nd-order shelves whose cut mirrors their boost. `fi.low_shelf` and `fi.high_shelf` reach only about a quarter of a cut at the corner (−2.7 dB for −12 dB, against +9.2 dB for +12 dB), and the pedal's EQ is documented as symmetric |
| Output safety limiter | Reused (`pk.safety`) |

The two clipping stages each sit in their own oversampler, with the inter-stage low-pass between them, so the latency is 2 × 32 = 64 samples. The clean path is delayed by the same `latencySamples`.

## 4. Constants

The documented values (the EQ frequencies and range) and the reported ones (the Character range, the zener clip) are in the [circuit notes](circuit-notes.md), section 3. Everything else is chosen:

| Constant | Value | Confidence | Intent |
|---|---|---|---|
| `biteHpLo`, `biteHpHi` | 10 Hz, 40 Hz | Chosen | Bite 0 is out of the way. Bite 100 sits just below low E (41 Hz), so the open string survives and rumble below it stops modulating the clippers |
| Bite subsonic order, Q | 2nd order, 0.707 | Chosen | Steep enough to cut 15 Hz by 15 dB, without a resonant bump |
| `charRange` | ±15 dB | Reported range [3], chosen law | Linear in dB across the knob, 0 dB at noon |
| `charFLo`, `charFHi`, `charQ` | 250 Hz, 700 Hz, 0.7 | Chosen | A low-mid scoop at the "deep" end and an upper-mid push at the "crunch" end, gliding log-uniformly between them. The direction is a guess (open question 1) |
| `driveMaxDb` | 30 dB | Chosen | Drive 0 is almost clean (0.4 % THD on a −12 dBFS note), Drive 100 is heavily clipped (42 %) |
| `charGainDb` | 12 dB | Chosen | "Above 12 o'clock increases the gain and crunch" [1]. 12 dB takes the default Drive from mild grit to heavy crunch |
| `v1` | ±1.2 V | Chosen | A soft first stage that rounds the peaks before the hard one, as two diode drops would |
| `interLp` | 6 kHz | Chosen | Takes the fizz off stage 1's harmonics before stage 2 squares them up |
| `g2` | 4 | Chosen | Stage 2 starts to clip only once stage 1 is near its limit, so low Drive stays soft |
| `railV`, `railN` | ±3.1 V, 4 | Inferred level, chosen knee | The op-amp swing on 9 V, as in BassPreamp. A knee of 4 is close to a hard clip |
| `bloomThr` | 0.6 × `railV` | Chosen | The bias moves only on peaks that already push stage 2 towards its rails, so light playing is untouched |
| `bloomMax` | 0.25 × `railV` | Chosen | Large enough for strong second harmonic (−25 dBc on a hard note). At 0.5 × `railV`, a sudden jump of Character from 100 to 0 left a charged bias on a smaller signal and made a 7 dB burst of high harmonics (the common zipper test allows 6) |
| `bloomAtt`, `bloomRel` | 20 ms, 150 ms | Chosen | The attack transient stays symmetric and the bloom follows it, then fades within about a second |
| `presF`, `presDb`, `presQ` | 2.5 kHz, +6 dB, 0.7 | Chosen | "Definition" in the upper mids, below the speaker sim's roll-off |
| `cabLp1F`, `cabLp1Q` / `cabLp2F`, `cabLp2Q` | 4.5 kHz, 0.707 / 6 kHz, 0.6 | Chosen | A smooth roll-off with no peak [1]: −3 dB at 3.7 kHz, −28 dB at 10 kHz |
| `cabHpF`, `cabHpQ` | 30 Hz, 0.6 | Chosen | A closed cabinet's low-end limit, low enough to keep a low B's fundamental (31 Hz) |
| `drvTrim` | 0.42 | Chosen, by measurement | The preamp path matches the clean path's loudness at the defaults (K-weighted, bass line at −12 dBFS) |
| `bypTrim` | 1.0 | Chosen, by measurement | Cab Bypass is within 0.8 dB of the voiced path at every Drive and Character setting measured, so no trim is needed |
| `midQ` | 0.7 | Chosen | A broad mid band, like most active bass EQs |
| Defaults | Drive 30 %, Character 50 %, Bite 100 %, Blend 100 % | Chosen | A warm, lightly driven sound (5.7 % THD); Bite on as in all of the manual's sample settings [1] |

## 5. Measurable targets

Checked in `tests/basseras/test_character.py`, `test_bite.py`, `test_freqresp.py` and `test_harmonics.py`. The measured values are from the first build (October 2026).

1. **Character EQ.** Relative to Character 50, less the extra gain, the response's extreme lies within 1 dB and a quarter-octave of the chosen centre and gain. Measured: −15.0 dB at 252 Hz (Character 0), −7.5 dB at 325 Hz, +7.5 dB at 539 Hz, +15.0 dB at 697 Hz (Character 100).
2. **Monotonic sweep.** The gain at each setting's own centre rises with the knob and spans at least 20 dB. Measured: 30.0 dB.
3. **Character adds drive.** At Drive 30, THD of a −12 dBFS 110 Hz tone rises at least 6 dB from Character 50 to 100. Measured: +15.7 dB (5.7 % to 34.3 %).
4. **Bite.** Bite 100 over Bite 0: at least 12 dB less at 15 Hz and 6 dB less at 25 Hz, within 1 dB from 100 to 500 Hz, and a presence peak of +4 to +8 dB between 1.5 and 4 kHz. Measured: −15.6 dB, −8.1 dB, within 0.27 dB, +6.0 dB at 2.5 kHz. Bite 50 gives +3.0 dB.
5. **Bite tightens.** At Drive 100, with a 15 Hz tone at −12 dBFS under a 220 Hz note, the rumble's intermodulation sidebands fall by at least 10 dB. Measured: −53.5 dBc to −78.4 dBc.
6. **Speaker sim.** −3 dB between 3.5 and 5.5 kHz, at least 20 dB down at 10 kHz relative to 1 kHz, and smooth (peak under 1 dB) from 80 Hz to 3 kHz. Measured: −3 dB at 3.72 kHz, −28.0 dB at 10 kHz, peak +0.07 dB.
7. **EQ.** With Blend 0, Mid reaches ±12.0 dB at 1 kHz; Low and High reach ±5.9 dB at 125 Hz and 3.2 kHz and ±11.7 to 12.0 dB a factor of 3 beyond, with cut mirroring boost.
8. **Aliasing.** 4x oversampling lowers the worst alias against a 1x build by at least 15 dB, and keeps it below −60 dBc at 441 Hz with the speaker sim on, at Drive, Character and Bite 100. Measured: 49.7 dB lower, −89.9 dBc. At 1.1 kHz it is −52.2 dBc (21.5 dB better than 1x).

## 6. Dynamics and feel

Checked in `tests/basseras/test_dynamics.py` (see [Designing for feel](../development/designing-for-feel.md)).

1. **The bloom.** A 110 Hz tone at −12 dBFS for 0.6 s: at Character 100 the second harmonic in the loud section is above −30 dBc and at least 30 dB above Character 50. Measured: −25.5 dBc against −84.2 dBc.
2. **It builds after the attack.** H2 comes within 3 dB of its steady value 10 to 150 ms after the onset. Measured: 33 ms. On a plucked note it peaks 283 ms in (target: later than 30 ms).
3. **It lingers, then fades.** 100 ms after the loud section H2 is at least 20 dB above Character 50, and 1.1 s after it has fallen below −60 dBc. Measured: −63.6 dBc against −88.7 dBc, then −80.8 dBc.
4. **Limiting.** At Drive 100 the output rises less than 0.5 dB per dB of input from −20 to 0 dBFS (the manual: the circuit "limits transient peaks for an even meter reading" [1]). Measured: 0.01 dB per dB.

Why the bias is on stage 2: with the bias on stage 1, either a coupling high-pass between the stages turned every Character move into a DC step that stage 2 clipped on one side (a burst of high harmonics in the zipper test), or, with the stages DC-coupled, stage 2 clipped the shifted wave back towards symmetry and H2 fell from −18 to −43 dBc. On the last clipper, the DC from the asymmetry meets only the 5 Hz high-pass after it.

## 7. Open questions

Only listening can answer these.

- Is the Character sweep the right way round? A scoop at the deep end and a push at the crunch end is a guess (circuit notes, open question 1).
- Are 250 Hz and 700 Hz the right ends of the glide, and is Q 0.7 too broad?
- Is the bloom audible as "attack and feel" or as a change of tone? Try `bloomMax` from 0.15 to 0.3 × `railV`, and `bloomRel` from 80 to 300 ms.
- Does the speaker sim sound like a 10-inch cabinet? Try `cabLp1F` from 3.5 to 5.5 kHz.
- Is the default Drive (30 %) clean enough for a DI?
- Does Bite's 40 Hz corner thin out a five-string's low B (31 Hz) too much when Blend is at 100?
