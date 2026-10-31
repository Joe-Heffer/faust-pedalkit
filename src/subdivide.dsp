// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// SubDivide: a monophonic octave-down for guitar and bass. Two flip-flop
// dividers make sub-octaves one and two octaves below the note, and a
// low-pass that follows the detected pitch keeps them equally round across
// the neck.
//
// Original design (docs/subdivide/design-notes.md). It starts from the
// principle of the classic analogue dividers (filter the input, square it,
// halve the frequency with flip-flops), not from any one circuit's values.
// The departures: the dividers toggle at the zero crossing of the filtered
// signal, after a level-relative arm, with a sub-sample edge; a Shape control
// that crossfades between the divided square and the input itself with every
// other cycle inverted; a pitch-tracking 4th-order low-pass on each sub; a
// gate with hysteresis; and a fade above the Range note.
//
// Signal flow (mono):
//
//   in -> DC block -+-------------------------------------------- Direct ---+
//                   |                                                       |
//                   +-> high-pass 20 Hz -> low-pass 4th order at Range      |
//                       = detector signal d, peak envelope e                |
//                       -> arm below -hyst * e, fire at the next upward     |
//                          zero crossing -> flip-flop 1 (/2) -> flip-flop 2 (/4)
//                          -> period between fires = pitch estimate f       |
//                       sub n = mix(e * s_n, d * s_n; Shape)                |
//                       -> tracking low-pass at Tone * f / 2^n              |
//                       -> * gate(e, Gate) * fade above Range -> Sub n -----+
//                                                                           |
//   -> DC block on the subs -> sum -> Level -> safety limiter -> out <------+
//
// No oversampling and no latency: the polarity of each sub flips where the
// detector signal crosses zero, so the sub has a corner rather than a step,
// and the edge is placed between samples (see "Dividers" below).

declare name        "SubDivide";
declare description "Octave-down with two pitch-tracked sub-octaves for guitar and bass";
declare author      "Joe Heffer";
declare license     "MIT";              // SPDX identifier (see tools/fix-ttl.py)
declare version     "0.1.0";
declare lv2class    "PitchPlugin";
declare homepage    "https://github.com/Joe-Heffer/faust-pedalkit";

import("stdfaust.lib");
pk = library("pedalkit.lib");

//============================================================================
// Controls. Every value is smoothed with si.smoo to avoid zipper noise.
//============================================================================

// Direct has a -60 dB floor rather than an "off": the dry path is always
// there, so the host and the latency test always see the same delay (0).
direct = hslider("[0]Direct [unit:dB] [tooltip:Level of the unprocessed signal]",
                 0, -60, 6, 0.1) : ba.db2linear : si.smoo;
sub1   = hslider("[1]Sub 1 [unit:%] [tooltip:Level of the sub-octave one octave down]",
                 70, 0, 100, 0.1) / 100 : si.smoo;
sub2   = hslider("[2]Sub 2 [unit:%] [tooltip:Level of the sub-octave two octaves down]",
                 0, 0, 100, 0.1) / 100 : si.smoo;
range  = hslider("[3]Range [unit:Hz] [scale:log] [tooltip:Highest note the dividers follow. Low for bass, high for guitar]",
                 700, 200, 1500, 1) : si.smoo;
tone   = hslider("[4]Tone [unit:%] [tooltip:Tracking low-pass on the subs, from 1x (0) to 4x (100) each sub's own frequency]",
                 50, 0, 100, 0.1) / 100 : si.smoo;
shape  = hslider("[5]Shape [unit:%] [tooltip:0 = divided square wave, 100 = the input with every other cycle inverted]",
                 50, 0, 100, 0.1) / 100 : si.smoo;
gate   = hslider("[6]Gate [unit:dB] [tooltip:The subs fade out when the detector signal falls below this level]",
                 -55, -80, -20, 0.1) : ba.db2linear : si.smoo;
level  = hslider("[7]Level [unit:dB] [tooltip:Output level]",
                 0, -24, 12, 0.1) : ba.db2linear : si.smoo;

//============================================================================
// Constants. docs/subdivide/design-notes.md (section 4) gives the confidence
// and intent of each. All are chosen unless marked otherwise.
//============================================================================

// Detector. A 2nd-order high-pass at 20 Hz takes out handling noise but
// passes low B (30.9 Hz) with under 1 dB of loss; a 4th-order Butterworth
// low-pass at Range keeps the fundamental and pushes the 2nd harmonic of the
// highest tracked note 24 dB down, so it can't add zero crossings.
detHpF    = 20;
detLpN    = 4;

// Peak envelope of the detector signal: 1 ms attack follows a pick, 50 ms
// release outlasts one period of low B (32 ms), so the envelope holds
// through each cycle rather than following the waveform.
envAtt    = 0.001;   // seconds
envRel    = 0.05;    // seconds

// Arm threshold, as a fraction of the envelope. A divider fires only at an
// upward zero crossing that follows a dip below -hyst * e. Ripple from the
// 2nd and 3rd harmonics, which can cross zero near the true crossing, stays
// above it. Scaling with e keeps the behaviour the same at any level.
hyst      = 0.25;

// Fastest allowed fire rate, as a multiple of Range: a crossing sooner than
// one period of 2 * Range after the last is ignored, so a note above Range
// can't make the dividers run at a harmonic.
maxRateMul = 2;

// Pitch estimate. Glide of the tracking filters' corners between notes, and
// the lowest and highest input pitch the estimate is clamped to.
pitchTau  = 0.005;   // seconds
pitchLo   = 25;      // Hz, below low B (30.9 Hz)

// Tracking low-pass: Tone sweeps the corner from 1x to 4x the sub's own
// frequency (log). 4th-order Butterworth (two sections, Q 0.541 and 1.307).
toneLoMul = 1;
toneHiMul = 4;
bwQ1      = 0.541;   // documented: 4th-order Butterworth pole pair Qs
bwQ2      = 1.307;

// Range fade: subs fall from full at Range to silent half an octave above.
fadeOct   = 0.5;

// Gate: opens above Gate, closes below Gate - 6 dB (hysteresis), and fades
// over 10 ms so it can't click.
gateHyst  = 0.5;     // 6 dB
gateTau   = 0.01;    // seconds

// Sub trims (chosen, measured). Each sub's fundamental matches the level of
// a sine at the input with Tone 50, at either end of Shape.
sqTrim    = 0.55;
flTrim    = 1.0;
sub1Trim  = 1.0;
sub2Trim  = 1.0;

outCeil   = 0.989;   // safety-limiter ceiling, about -0.1 dBFS

//============================================================================
// Detector.
//============================================================================

detector = fi.highpass(2, detHpF) : fi.lowpass(detLpN, range);
envelope = an.amp_follower_ar(envAtt, envRel);

//============================================================================
// Dividers. One state machine (letrec: on the right of each equation, a
// state variable is its value one sample earlier) holds:
//   arm  set when d < -hyst * e, cleared on a fire
//   cnt  samples since the last fire
//   s1   flip-flop 1, +/-1, toggles on every fire (input frequency / 2)
//   s2   flip-flop 2, +/-1, toggles when s1 rises (input frequency / 4)
//   per  input period in samples, measured between the last two fires
//   fr   sub-sample position of the last fire
// A fire is an upward zero crossing of d between the previous sample and
// this one, while armed, at least minPer samples after the last fire.
//============================================================================

minPer = ma.SR / (maxRateMul * range);

dividers(d, e) = (s1, s2, per, a)
letrec {
    'arm = ((arm > 0) | (d < -hyst * e)) & (fire(arm, cnt) == 0);
    'cnt = ba.if(fire(arm, cnt), 0, min(cnt + 1, 1e6));
    's1  = ba.if(fire(arm, cnt), ba.if(s1 > 0, -1, 1), ba.if(s1 == 0, 1, s1));
    's2  = ba.if(fire(arm, cnt) & (s1 < 0), ba.if(s2 > 0, -1, 1), ba.if(s2 == 0, 1, s2));
    'per = ba.if(fire(arm, cnt), cnt + 1 + fr - a, per);
    'fr  = ba.if(fire(arm, cnt), a, fr);
}
with {
    dm = d';
    fire(arm, cnt) = (arm > 0) & (dm <= 0) & (d > 0) & (cnt + 1 >= minPer);
    // Fraction of the last sample interval before the crossing, 0 to 1.
    a = ba.if((dm <= 0) & (d > 0), dm / min(dm - d, -1e-12), 0);
};

// A flip-flop output with its edge placed between samples: on the sample
// where s changes, the value is the interval's average, a * old + (1 - a) * new.
edge(s, a) = ba.if(s != s', a * s' + (1 - a) * s, s);

//============================================================================
// Subs.
//============================================================================

toneMul = toneLoMul * pow(toneHiMul / toneLoMul, tone);

track(fc) = fi.svf.lp(f, bwQ1) : fi.svf.lp(f, bwQ2)
with { f = max(5, min(fc, 0.45 * ma.SR)); };

// One sub: the divided square (e * s) or the inverted-cycle input (d * s),
// crossfaded by Shape, then low-passed at Tone times its own frequency.
oneSub(n, d, e, s, f) = (sqTrim * e * s) * (1 - shape) + (flTrim * d * s) * shape
                      : track(toneMul * f / pow(2, n));

gateGain(e) = o letrec { 'o = (e > gate) | ((o > 0) & (e > gate * gateHyst)); }
            : si.smooth(ba.tau2pole(gateTau));

// Range fade: 1 up to Range, 0 from fadeOct octaves above it.
fade(f) = max(0, min(1, 1 - log(f / range) / (log(2) * fadeOct)));

mixSubs(d, e, s1, s2, per, a) =
    (oneSub(1, d, e, edge(s1, a), f) * sub1 * sub1Trim
     + oneSub(2, d, e, edge(s2, a), f) * sub2 * sub2Trim)
    * gateGain(e) * fade(f)
with {
    // Input pitch from the measured period, clamped and glided.
    f = ma.SR / max(per, ma.SR / (2 * maxRateMul * range))
      : max(pitchLo) : si.smooth(ba.tau2pole(pitchTau));
};

subs(x) = mixSubs(d, e, s1, s2, per, a)
with {
    d = x : detector;
    e = d : envelope;
    s1 = dividers(d, e) : _, !, !, !;
    s2 = dividers(d, e) : !, _, !, !;
    per = dividers(d, e) : !, !, _, !;
    a = dividers(d, e) : !, !, !, _;
};

//============================================================================
// Mix and output.
//============================================================================

process = fi.dcblockerat(5)
        <: *(direct), (subs : fi.dcblockerat(5)) :> *(level)
        : pk.safety(outCeil);
