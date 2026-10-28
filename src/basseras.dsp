// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// BassEras: a bass preamp/DI whose Character control re-voices the whole
// preamp, from a deep, scooped stack through a warm, flat studio amp to a
// pushed, crunchy one, changing the pre-clip EQ, the gain and the attack
// together.
//
// Circuit-inspired. The control set, the EQ frequencies and the order of the
// stages follow the public manual and community notes on a well-known bass
// preamp/DI pedal (docs/basseras/circuit-notes.md); its clipping core is not
// public, so the stages themselves are chosen (docs/basseras/design-notes.md).
// The departures from that pedal are a Character control that also moves the
// clipper's bias on hard notes, a continuous Bite, and Cab Bypass.
//
// Signal flow (mono):
//
//   in -> DC block -+-> delay (latency match) --------------------------------+
//                   |                                                         +-> Blend
//                   +-> Bite subsonic high-pass (10 Hz -> 40 Hz)              |
//                       -> Character mid peak/cut (250 Hz -> 700 Hz, +/-15 dB)|
//                       -> stage 1 gain (Drive, plus Character above noon)    |
//                       -> 4x OS soft clip -> inter-stage low-pass            |
//                       -> stage 2 gain -> 4x OS rail clip -> DC block        |
//                          ^ bias pushed by hard notes <- Character           |
//                       -> Bite presence peak (2.5 kHz)                       |
//                       -> speaker sim (or Cab Bypass trim) -> trim ----------+
//   -> Low shelf 125 Hz -> Mid peak 1 kHz -> High shelf 3.2 kHz
//   -> Level -> safety limiter -> out
//
// The EQ follows the blend, so it stays active with Blend at 0, as on the
// pedal. Levels: 1.0 full scale is treated as 1 V peak at the circuit input.

declare name        "BassEras";
declare description "Bass preamp/DI with a Character control that sweeps amp voicings, gain and attack";
declare author      "Joe Heffer";
declare license     "MIT";              // SPDX identifier (see tools/fix-ttl.py)
declare version     "0.1.0";
declare lv2class    "AmplifierPlugin";
declare homepage    "https://github.com/Joe-Heffer/faust-pedalkit";

import("stdfaust.lib");
pk = library("pedalkit.lib");

//============================================================================
// Controls. Every value is smoothed with si.smoo to avoid zipper noise.
//============================================================================

level  = hslider("[0]Level [unit:dB] [tooltip:Output level]",
                 0, -40, 12, 0.1) : si.smoo;
blend  = hslider("[1]Blend [unit:%] [tooltip:0 = clean only, 100 = preamp only]",
                 100, 0, 100, 0.1) / 100 : si.smoo;
drive  = hslider("[2]Drive [unit:%] [tooltip:Gain into the preamp's two clipping stages]",
                 30, 0, 100, 0.1) / 100 : si.smoo;
charac = hslider("[3]Character [unit:%] [tooltip:Below 50 = deep and scooped, 50 = warm and flat, above 50 = pushed mids, more gain and a bias that blooms on hard notes]",
                 50, 0, 100, 0.1) / 100 : si.smoo;
low    = hslider("[4]Low [unit:dB] [tooltip:Low shelf at 125 Hz]",
                 0, -12, 12, 0.1) : si.smoo;
mid    = hslider("[5]Mid [unit:dB] [tooltip:Mid band at 1 kHz]",
                 0, -12, 12, 0.1) : si.smoo;
high   = hslider("[6]High [unit:dB] [tooltip:High shelf at 3.2 kHz]",
                 0, -12, 12, 0.1) : si.smoo;
bite   = hslider("[7]Bite [unit:%] [tooltip:Presence peak and subsonic filter in the preamp path. 100 = the pedal's switch on, 0 = off]",
                 100, 0, 100, 0.1) / 100 : si.smoo;
// A checkbox defaults to off, so the default keeps the speaker sim on.
cabByp = checkbox("[8]Cab Bypass [tooltip:Off = speaker sim on the preamp path; on = preamp path unfiltered, for a cabinet or impulse response]") : si.smoo;

//============================================================================
// Constants. docs/basseras/design-notes.md (section 4) and circuit-notes.md
// give the confidence of each: documented, reported, inferred or chosen.
//============================================================================

// Bite subsonic high-pass (chosen): 2nd-order Butterworth whose corner
// glides from 10 Hz (out of the way) to 40 Hz (just below low E) with Bite,
// so the clipper stops reacting to the lowest octave and tightens up.
biteHpLo   = 10;
biteHpHi   = 40;

// Character pre-clip EQ (range reported, shape chosen). Gain runs from
// -15 dB at 0 through 0 dB at 50 to +15 dB at 100, and the centre glides
// log-uniformly from 250 Hz to 700 Hz as it does.
charRange  = 15;
charFLo    = 250;
charFHi    = 700;
charQ      = 0.7;

// Gain law (chosen). Drive sweeps stage 1 log-uniformly from 0 to 30 dB;
// Character adds up to 12 dB more above noon, as the manual describes.
driveMaxDb = 30;
charGainDb = 12;
// Character above noon, 0 to 1. It sets the extra gain and the bias amount.
push       = max(0, 2 * charac - 1);
g1         = ba.db2linear(driveMaxDb * drive + charGainDb * push);

// Stage 1 (chosen): a soft tanh clip at +/-1.2 V, a "tube-like" first stage
// that rounds peaks before the harder stage 2 is reached.
v1         = 1.2;

// Bias bloom (chosen, the feel departure). Above noon, peaks into stage 2
// beyond bloomThr push its operating point by up to bloomMax, charging over
// bloomAtt and recovering over bloomRel. The clip turns asymmetric for the
// body of a hard note, adding second harmonic after the attack. bloomMax
// is held to a quarter of the rail: at half, a sudden jump of Character from
// 100 to 0 left a charged bias on a now smaller signal, and for about 50 ms
// stage 2 clipped one side only, a burst of high harmonics 7 dB over the
// steady state (tests/common/test_zipper.py allows 6).
bloomThr   = 0.6 * railV;
bloomMax   = 0.25 * railV;
bloomAtt   = 0.02;    // seconds
bloomRel   = 0.15;    // seconds

// Between the stages (chosen): a gentle low-pass that takes the fizz off
// stage 1 before stage 2 squares it up.
interLp    = 6000;

// Stage 2 (chosen gain, inferred clip). A TL07x on a ~9 V supply swings to
// about +/-3.1 V around its bias (as in BassPreamp); the reported zener pair
// (3.3 V plus a forward drop) would clip later, so the rails set the level.
g2         = 4;
railV      = 3.1;
railN      = 4;

// Bite presence peak (chosen): +6 dB at 2.5 kHz, Q 0.7, after the clippers.
presF      = 2500;
presDb     = 6;
presQ      = 0.7;

// Speaker sim (chosen to the documented "smooth, even" 10-inch response): two
// 2nd-order low-passes, -3 dB near 3.7 kHz with no peak, and a 2nd-order
// high-pass at 30 Hz for the cabinet's low-end limit.
cabLp1F    = 4500;
cabLp1Q    = 0.707;
cabLp2F    = 6000;
cabLp2Q    = 0.6;
cabHpF     = 30;
cabHpQ     = 0.6;

drvTrim    = 0.42;    // driven = clean level at the defaults (chosen, measured)
bypTrim    = 1.0;     // Cab Bypass loudness match at the defaults (chosen, measured)

// EQ (documented: +/-12 dB, 125 Hz, 1 kHz and 3.2 kHz). Shapes are chosen.
lowF       = 125;
midF       = 1000;
midQ       = 0.7;
highF      = 3200;

outCeil    = 0.989;   // safety-limiter ceiling, about -0.1 dBFS

//============================================================================
// Driven path.
//============================================================================

// 2nd-order analogue sections from a corner and a Q.
lp2(f, q) = pk.tf2a(0, 0, w * w, w / q, w * w, w) with { w = 2 * ma.PI * f; };
hp2(f, q) = pk.tf2a(1, 0, 0, w / q, w * w, w) with { w = 2 * ma.PI * f; };

subsonic  = hp2(biteHpLo * pow(biteHpHi / biteHpLo, bite), 0.707);
character = fi.peak_eq_cq(charRange * (2 * charac - 1),
                          charFLo * pow(charFHi / charFLo, charac), charQ);

clip1     = pk.oversample4(pk.softSat(v1));

// Stage 2: the rail clip moved off centre by the bloom bias (0 at or below
// noon). The bias sits on the last clipper on purpose. On stage 1, either a
// coupling high-pass between the stages turned each Character move into a DC
// step that stage 2 clipped on one side (a burst of high harmonics), or,
// DC-coupled, stage 2 clipped the shifted wave back towards symmetry and the
// second harmonic fell from -18 to -43 dBc. Here the DC from the asymmetry
// meets only the 5 Hz high-pass after the stage.
stage2    = pk.biased(pk.kneeClip(railV, railN));
bias      = pk.biasShift(bloomThr, bloomMax, bloomAtt, bloomRel) : *(push);
clip2     = *(g2) <: _, bias : pk.oversample4c(stage2);

presence  = fi.peak_eq_cq(presDb * bite, presF, presQ);

cab       = lp2(cabLp1F, cabLp1Q) : lp2(cabLp2F, cabLp2Q) : hp2(cabHpF, cabHpQ);
// The speaker sim, or with Cab Bypass a plain trim in its place. The
// smoothed switch crossfades between the two, so toggling doesn't click.
voicing   = _ <: cab, *(bypTrim) : si.interpolate(cabByp);

driven = subsonic : character : *(g1)
       : clip1
       : fi.lowpass(1, min(interLp, 0.45 * ma.SR))
       : clip2 : fi.dcblockerat(5)
       : presence : voicing : *(drvTrim / g2);

//============================================================================
// Clean path: full-range, delayed to line up with the two oversamplers.
//============================================================================

latencySamples = 2 * pk.os4Latency;

clean = @(latencySamples);

//============================================================================
// Blend, EQ and output.
//============================================================================

mix  = _ <: clean, driven : si.interpolate(blend);

tone = pk.lowShelf2(low, lowF)
     : fi.peak_eq_cq(mid, midF, midQ)
     : pk.highShelf2(high, highF);

// Reports the oversamplers' delay to the host, which can then compensate it.
latency = latencySamples
        : hbargraph("Latency [unit:samples] [lv2:reportsLatency] [lv2:integer]", 0, 256);

process = fi.dcblockerat(5) : mix : tone : *(ba.db2linear(level))
        : pk.safety(outCeil) : attach(_, latency);
