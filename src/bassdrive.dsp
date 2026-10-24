// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// BassDrive: a bass overdrive with a clean/driven blend and a two-band EQ.
//
// Modelled on a well-known compact two-band bass overdrive pedal, using only
// public circuit analyses and measurements. See docs/bassdrive/circuit-notes.md
// for the sources and for which values are documented, reported, inferred or
// chosen.
//
// Signal flow (mono):
//
//   in -> DC block -+-> delay (latency match) ------------------------+
//                   |                                                 +-> Balance
//                   +-> stage 1 (pre-emphasis gain) -> 4x OS clipper -+
//                       -> DC block -> post low-pass -> trim
//   -> Bass / fixed mid scoop / Treble -> Level -> safety limiter -> out
//
// Levels: 1.0 full scale is treated as 1 V peak at the circuit input.

declare name        "BassDrive";
declare description "Bass overdrive with clean blend and two-band EQ";
declare author      "Joe Heffer";
declare license     "MIT";              // SPDX identifier (see tools/fix-ttl.py)
declare version     "0.1.0";
declare lv2class    "DistortionPlugin";
declare homepage    "https://github.com/Joe-Heffer/faust-pedalkit";

import("stdfaust.lib");
pk = library("pedalkit.lib");

//============================================================================
// Controls. Every value is smoothed with si.smoo to avoid zipper noise.
//============================================================================

level   = hslider("[0]Level [unit:dB] [tooltip:Output level]",
                  0, -40, 12, 0.1) : si.smoo;
balance = hslider("[1]Balance [unit:%] [tooltip:0 = clean only, 100 = driven only]",
                  50, 0, 100, 0.1) / 100 : si.smoo;
gain    = hslider("[2]Gain [unit:%] [tooltip:Amount of drive]",
                  50, 0, 100, 0.1) / 100 : si.smoo;
bass    = hslider("[3]Bass [unit:dB] [tooltip:Low band around 110 Hz]",
                  0, -12, 12, 0.1) : si.smoo;
treble  = hslider("[4]Treble [unit:dB] [tooltip:High shelf above 2.5 kHz]",
                  0, -15, 15, 0.1) : si.smoo;

//============================================================================
// Circuit constants (see circuit-notes.md, sections 3 to 7).
//============================================================================

R31      = 3.3e3;     // pre-emphasis shunt resistor (reported)
C10      = 33e-9;     // pre-emphasis shunt capacitor (reported)
C8       = 300e-12;   // feedback capacitor (reported)
fcEmph   = 1 / (2 * ma.PI * R31 * C10);   // about 1.46 kHz

// Ratio Rf/R31 as a function of Gain (chosen). Modelled as a 1 MOhm log-taper
// pot (about 10 % of its resistance at noon) plus 3.3 kOhm in series:
// Rf/R31 runs from 1 to about 304, roughly 30 at noon.
hfGain   = 1 + 303 * (pow(10, 2 * gain) - 1) / 99;
Rf       = hfGain * R31;
fcFb     = min(1 / (2 * ma.PI * Rf * C8), 0.45 * ma.SR);

railV    = 4.0;       // stage 1 headroom on a 9 V supply (chosen)
stage2G  = 3.0;       // stage 2 fixed gain (chosen, tuned by measurement)
ledPos   = 1.7;       // positive clipping level, red LED (reported range)
ledNeg   = 0.8;       // negative clipping level of the biased stage (chosen)
negKnee  = 6;         // hardness of the negative knee (chosen)

postLP   = min(5000, 0.45 * ma.SR);   // driven-path post-filter corner (chosen),
                                     // kept below Nyquist at low sample rates
drvTrim  = 0.28;      // driven within ~1.5 dB of clean at Gain 0-50 % (measured)

bassF    = 110;   bassQ  = 0.9;   // reported centre of the Low band
scoopF   = 350;   scoopQ = 0.7;   // reported mid scoop
scoopDB  = -6;                    // reported depth; tune to taste
trebF    = 2500;                  // shelf corner (chosen)
topLP    = min(12000, 0.45 * ma.SR);  // caps the treble boost (chosen), kept
                                     // below Nyquist at low sample rates

outCeil  = 0.989;     // safety-limiter ceiling, about -0.1 dBFS

//============================================================================
// Driven path.
//============================================================================

// Stage 1: non-inverting gain with a series RC shunt (R31, C10) and a
// feedback capacitor (C8). Its transfer function is
//   1 + (Rf/R31) * HP(fcEmph) * LP(fcFb)
// so the lows pass at unity and the upper register is driven.
stage1 = _ <: _, (fi.highpass(1, fcEmph) : fi.lowpass(1, fcFb) : *(hfGain)) :> _;

// Memoryless clipping chain, run inside the oversampler: stage 1 headroom,
// stage 2 gain, then soft LED clipping above zero and a harder knee below.
// That gives light, mostly odd distortion at low Gain and even-leaning
// distortion by noon, as reported by the measurements in the notes.
shaper = pk.softSat(railV) : *(stage2G) : pk.asymSoftHard(ledPos, ledNeg, negKnee);

driven = stage1
       : pk.oversample4(shaper)
       : fi.dcblockerat(5)
       : fi.lowpass(2, postLP)
       : *(drvTrim);

//============================================================================
// Clean path: full-range, only delayed to line up with the driven path.
//============================================================================

clean = @(pk.os4Latency);

//============================================================================
// Tone stack and output.
//============================================================================

tone = fi.peak_eq_cq(bass, bassF, bassQ)
     : fi.peak_eq_cq(scoopDB, scoopF, scoopQ)
     : fi.high_shelf(treble, trebF)
     : fi.lowpass(1, topLP);

blend = _ <: clean, driven : *(1 - balance), *(balance) :> _;

// Reports the oversampler's delay to the host, which can then compensate it.
latency = pk.os4Latency
        : hbargraph("Latency [unit:samples] [lv2:reportsLatency] [lv2:integer]", 0, 256);

// The DC blocker sits at 5 Hz rather than fi.dcblocker's ~35 Hz, which would
// already take the edge off a low E (41 Hz) or a low B (31 Hz).
process = fi.dcblockerat(5) : blend : tone : *(ba.db2linear(level))
        : pk.safety(outCeil) : attach(_, latency);
