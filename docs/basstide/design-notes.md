# Design notes: BassTide

BassTide is an **original** effect: a through-zero flanger for bass, with no single reference device.

!!! warning "Draft"
    This is the initial concept. The DSP was written without a Faust compiler to hand, and none of the measured values below exist yet. Every target in section 5 is still to be measured, and the sources in section 2 still need checking.

## 1. The idea

A flanger mixes a signal with a copy of itself through a short delay that moves. The sum is a comb filter: notches at odd multiples of 1/(2Δ), where Δ is the time difference between the two copies, sweeping as Δ moves. A phaser sweeps a handful of notches. A flanger sweeps dozens, so it moves more on a bass, whose harmonics are dense.

*Through-zero* flanging delays the dry signal too, so the wet copy can run ahead of it as well as behind it. As Δ passes through zero the notches spread apart and leave the top of the band, and on the far side they come back. That passage gives the “jet” swoosh of the original two-tape-machine technique [4], which a flanger whose wet copy is always behind the dry cannot make.

On bass, the problem is the low end. A deep comb notches out the fundamental of a low E (41 Hz) or a low B (31 Hz), and the note loses its weight. BassTide splits the signal with a Linkwitz–Riley crossover [3] and keeps everything below **Crossover** (80 Hz to 400 Hz) dry, mono and unmodulated. Only the harmonics and the attack are flanged, which is where a comb is audible on a bass anyway.

The second idea is **Follow**. At 0 % a steady LFO sweeps the comb through zero and back, like any flanger. At 100 % the LFO stops and each note starts its own sweep: the pick throws the wet copy out behind the dry, and it glides back to the zero point over the **Glide** time. At zero the wet and the dry are the same signal and the comb vanishes, so the attack swooshes and the sustain is clean. A harder pick throws the sweep further. A note played softly barely moves it. In between, Follow blends the two.

What a player gets that existing flangers don't give them:

- a full-depth, through-zero comb that leaves the bottom octave untouched
- a sweep that follows their playing, with a clean sustain that a free-running LFO never gives

## 2. Prior art and inspirations

Still to be completed. These are the starting points, all to be checked:

1. J. Dattorro, “Effect Design, Part 2: Delay-Line Modulation and Chorus”, *Journal of the Audio Engineering Society* 45(10), 1997 ([PDF](https://ccrma.stanford.edu/~dattorro/EffectDesignPart2.pdf)). Modulated delay lines, interpolation and the flanger as a comb filter.
2. J. O. Smith, *Physical Audio Signal Processing*, “Flanging” ([online](https://ccrma.stanford.edu/~jos/pasp/Flanging.html)). The comb filter's notch frequencies as a function of delay.
3. S. Linkwitz, notes on active crossovers ([linkwitzlab.com](https://www.linkwitzlab.com/filters.htm)). The 4th-order Linkwitz–Riley split, whose bands sum to an all-pass. BassGrit already uses it.
4. “Flanging”, *Wikipedia* ([article](https://en.wikipedia.org/wiki/Flanging)). The history of tape flanging with two machines, including the through-zero effect when the two tapes pass in and out of sync. To be replaced by a primary source.
5. Envelope-controlled effects in general (envelope filters, auto-wah), where the player's dynamics set the sweep instead of an LFO. A source for the idea of an onset-triggered sweep is still to be found.
6. Faust `delays.lib` documentation ([faustlibraries.grame.fr](https://faustlibraries.grame.fr/libs/delays/)), for `de.fdelay3` (third-order Lagrange fractional delay).

## 3. Block diagram

```text
in → DC blocker (5 Hz)
   ├─ LR4 low-pass (Crossover) → delay zeroSamples ─────────────────────────┐
   ├─ LR4 high-pass ┬─ delay zeroSamples × (1 − Depth/2) ───────────────────┤
   │                └─ fractional delay tau, Feedback round it × Depth/2 ───┤
   └─ onset detector → note sweep ─┐                                         │
                         LFO (Rate) ┴→ s = Sweep × mix(LFO, sweep; Follow)   │
                                       → tau = zeroSamples + offset(s)       │
→ sum → Level → safety limiter (≤ −0.1 dBFS) → out
```

| Block | New or reused |
|---|---|
| DC blocker, `fi.dcblockerat(5)` | Reused (`fi` library) |
| Linkwitz–Riley 4th-order split | Reused from BassGrit (the same two lines). A candidate for `pedalkit.lib` |
| Fractional delay with feedback, `de.fdelay3` | New in this file (`de` library) |
| LFO, `os.osc` | Reused (`os` library) |
| Onset detector (fast against slow envelope) | New in this file. A candidate for `pedalkit.lib` |
| Note sweep (charge, release, smooth) | New in this file. A candidate for `pedalkit.lib` |
| Through-zero offset law | New in this file |
| Output safety limiter | Reused (`pk.safety`) |

The candidates stay in the `.dsp` for this draft, so that a mistake in untested code can't break the other effects' builds. Once they compile and pass their tests, the crossover, the onset detector and the note sweep should move to `pedalkit.lib`, with BassGrit switched to the shared crossover.

BassTide is linear in the audio. It has no waveshaper, so it doesn't oversample. Its only latency is the dry delay.

## 4. Constants

All values are **chosen**: there is no reference device. The intent of each one is below, with what to retune by ear.

### Delay geometry

| Constant | Value | Confidence | Intent |
|---|---|---|---|
| `zeroSamples` | 96 samples (2 ms at 48 kHz) | Chosen | The dry delay, which is the through-zero point and the reported latency. It sets how far the wet copy can run ahead. With the wet 94 samples ahead the first notch is at 255 Hz, just above the default crossover, so the lead half of the sweep reaches the bottom of the flanged band. It stays within the 128-sample latency budget of `tests/common/test_latency.py`. It is fixed in samples, as the oversamplers' latency is, so at 96 kHz the lead is only 1 ms. |
| `minTap` | 2 samples | Chosen | The shortest wet delay. Third-order Lagrange interpolation needs at least one sample of delay; two leave a margin. |
| `leadMax` | `zeroSamples − minTap` = 94 samples | Chosen | How far the wet can run ahead of the dry. |
| `lagMaxSec` | 8 ms (384 samples at 48 kHz) | Chosen | How far the wet can trail the dry. The first notch is then at 62.5 Hz, below the crossover, so the comb is dense across the whole flanged band. Typical flangers sweep up to about 10 ms [2]; longer starts to sound like chorus or slapback. |
| `maxDelay` | 4096 samples | Chosen | Buffer length. `zeroSamples` + 8 ms is 1632 samples at 192 kHz. |
| Offset law | s · \|s\| · (`lagMax` for s ≥ 0, `leadMax` for s < 0) | Chosen | Spends more of the sweep near zero, where the notch frequencies change fastest, and has no kink at zero. |

### Sweep

| Constant | Value | Confidence | Intent |
|---|---|---|---|
| Rate | 0.05 Hz to 5 Hz, default 0.3 Hz, log | Chosen | From a slow wash to a fast warble. |
| Sweep | 0 to 100 %, default 70 % | Chosen | Width of the sweep either side of zero. At 70 % the LFO reaches 49 % of `lagMax` and `leadMax` (the offset law squares it). |
| Follow | 0 to 100 %, default 100 % | Chosen | Blend of the LFO and the note sweep. The default is the headline behaviour. It also means a steady input rests at the zero point, so the common latency test sees the dry tap. |
| Glide | 50 ms to 2 s, default 400 ms, log | Chosen | Time scale of the note sweep. At 400 ms the sweep peaks about 150 ms into a note and is back near zero after about 1 s (calculated from the two time constants below, still to be measured). At 50 ms the delay moves so fast that the wet copy is pitch-shifted by up to about half (Doppler). |
| `fastAtt`, `fastRel` | 1 ms, 10 ms | Chosen | The fast envelope follows the pick. 10 ms is short of a low E's half period (12 ms), so on a sustained low note the fast envelope ripples between about 0.3 and 1 times the peak and never reaches twice the slow envelope. |
| `slowAtt`, `slowRel` | 50 ms, 200 ms | Chosen | The slow envelope lags a new note by tens of milliseconds, which is what makes the onset visible, and follows a note's decay. |
| `onsetRatio` | 2 (6 dB) | Chosen | How far the fast envelope has to jump above the slow one to count as a new note. Lower makes the sweep restart on ghost notes and string noise, higher misses legato notes. |
| `onsetFloor` | 10⁻⁴ (−80 dBFS) | Chosen | Keeps the ratio finite on silence. |
| `levelRef` | 0.1 (−20 dBFS) | Chosen | How hard you have to play to get the full sweep: tanh(envelope / `levelRef`) is 0.76 at −20 dBFS and 0.1 at −40 dBFS. |
| `holdAtt` | 2 ms | Chosen | How fast the sweep target jumps up on an onset. The smoother after it limits how fast the delay moves. |
| `glideHold`, `glideSmooth` | 0.5, 0.25 of Glide | Chosen | The release of the target and the smoother after it. Two cascaded one-poles with time constants τ₁ = 2τ₂ give a bump 2(e^(−t/τ₁) − e^(−t/τ₂)) that peaks at τ₁ ln 2 with height 0.5. |
| `bumpNorm` | 1.7 | Chosen | Scales the bump so a strong onset reaches the full sweep, after the slow envelope's ~35 ms of onset adds to the 0.5 peak of the ideal bump. The result is limited to 1. To be checked by measurement. |

### Mix and output

| Constant | Value | Confidence | Intent |
|---|---|---|---|
| Depth | 0 to 100 %, default 100 % | Chosen | Wet weight Depth/2 and dry weight 1 − Depth/2 in the high band. At 100 % they are equal, so the notches are full nulls and the zero point gives exactly the dry signal: no level jump when the sweep comes to rest. |
| Feedback | −90 to +90 %, default 0 | Chosen | Feedback round the wet delay. Positive raises peaks between the notches (ringing, metallic), negative moves them to odd multiples (hollow). The peaks reach 1/(1 − \|Feedback\|), +20 dB at 90 %, so Level and the safety limiter matter there. At rest the loop delay is 97 samples, so with Feedback up a held note keeps a static comb about 495 Hz apart. |
| Crossover | 80 Hz to 400 Hz, default 200 Hz, log | Chosen | Below this the signal is dry. 200 Hz keeps the fundamentals of every open string on a five-string bass (31 Hz to 98 Hz) and most of the first harmonics out of the comb. |
| Level | −20 to +12 dB, default 0 dB | Chosen | Output trim, mainly for high Feedback. |
| `outCeil` | 0.989 | Chosen | Safety-limiter ceiling, about −0.1 dBFS, as in every effect. |

## 5. Measurable targets

These are checked in `tests/basstide/test_targets.py`, `test_freqresp.py` and `test_harmonics.py`. None has been measured yet.

1. **Transparent at rest.** With Sweep 0 and Feedback 0, the response is the crossover's all-pass: flat within 0.1 dB from 20 Hz to 20 kHz at Depth 0, 50 and 100.
2. **The low band is untouched.** With the LFO running (Follow 0, Sweep 100, Depth 100), the response from 30 Hz to 80 Hz is within 0.5 dB of Depth 0.
3. **Through zero.** With the LFO running (Follow 0, Sweep 100), the wet tap's offset from the dry tap, measured in short windows, reaches at least 80 samples ahead and at least 330 samples behind over one cycle.
4. **Notches are deep.** In the same windows, with the wet more than 20 samples behind, the deepest notch above 400 Hz is at least 25 dB below the dry level.
5. **Each note starts its own sweep.** With Follow 100, Sweep 100 and Glide 400 ms, a noise burst at −15 dBFS RMS from silence throws the wet tap at least 250 samples behind. The furthest point comes between 0.2 and 0.8 × Glide after the onset.
6. **And glides back.** By 3 × Glide after the onset, the wet tap is within 20 samples of the dry.
7. **Harder playing sweeps further.** The same burst at −40 dBFS RMS moves the wet tap less than 60 samples.
8. **Linear.** At the defaults, a 110 Hz sine at −12 dBFS comes out with every harmonic below −80 dBc.

## 6. Open questions

Only listening can answer these.

- Is 200 Hz the right default Crossover? Does the join between the dry low band and the flanged high band sound like one instrument, or like two?
- Does the note sweep feel like the bass responding to the hand? The constants to change are Glide, `onsetRatio`, `levelRef` and `bumpNorm`.
- The note sweep only goes behind the dry and back to zero, so in Follow mode the jet sound comes from the approach to zero, not from crossing it. Would a sweep that starts ahead, crosses zero and settles be more exciting, or would it sound like a pitch bend on every note?
- How much Doppler is acceptable? At short Glide the wet copy's pitch bends noticeably on the way out and back.
- With Feedback up, a held note keeps a static comb at the zero point. Is that a welcome colour or should Feedback fade out as the sweep comes to rest?
- Should the zero point (`zeroSamples`) scale with sample rate, so the lead is the same time at 96 kHz? That would change the reported latency with the rate.
- Would a stereo version (wet and dry panned, or two sweeps in opposite directions) be worth the extra channel?
