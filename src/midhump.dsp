// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// MidHump: a mid-hump overdrive, circuit-inspired, with an optional clean blend.
//
// The clipping stage and tone filters follow public circuit analyses of a
// well-known green overdrive pedal (docs/midhump/circuit-notes.md). With Blend
// at 0 the plugin is that model. Blend adds a full-range clean path, which the
// pedal does not have (docs/midhump/design-notes.md).
//
// Signal flow (mono):
//
//   in -> input high-pass -+-> delay (latency match) -----------+
//                          |                                    +-> sum
//                          +-> 720 Hz HP -> feedback LP -> gain -> 4x OS diode clip
//   (sum of input and clipped feedback branch = the op-amp output)
//   -> 723 Hz passive LP -> Tone shelf -> DC block -> + Blend x clean
//   -> Level -> safety limiter -> out
//
// Levels: 1.0 full scale is treated as 1 V peak at the circuit input.

declare name        "MidHump";
declare description "Mid-hump overdrive with optional clean blend";
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

drive = hslider("[0]Drive [unit:%] [tooltip:Amount of drive]",
                50, 0, 100, 0.1) / 100 : si.smoo;
tone  = hslider("[1]Tone [unit:%] [tooltip:0 = dark, 100 = bright]",
                50, 0, 100, 0.1) / 100 : si.smoo;
level = hslider("[2]Level [unit:dB] [tooltip:Output level]",
                0, -40, 12, 0.1) : si.smoo;
blend = hslider("[3]Blend [unit:%] [tooltip:Adds a full-range clean signal. 0 = the circuit as published]",
                0, 0, 100, 0.1) / 100 : si.smoo;

//============================================================================
// Constants (see circuit-notes.md and design-notes.md for the confidence of
// each one: reported, inferred or chosen).
//============================================================================

// Input coupling (inferred): 20 nF into 510 kOhm.
fcIn     = 1 / (2 * ma.PI * 510e3 * 20e-9);   // about 15.6 Hz

// Clipping stage (reported): non-inverting, gain 1 + Zf/Zg.
R4       = 4.7e3;     // grounded leg resistor
C3       = 47e-9;     // grounded leg capacitor
R6       = 51e3;      // fixed part of the feedback resistance
Rpot     = 500e3;     // Drive pot
C4       = 51e-12;    // feedback capacitor
fcHP     = 1 / (2 * ma.PI * R4 * C3);         // about 720 Hz

// Drive pot law (chosen): log taper, about 9 % of the pot at noon.
Rd       = Rpot * (pow(10, 2 * drive) - 1) / 99;
Rf       = R6 + Rd;
gainRatio = Rf / R4;                          // 10.9 to 118.2 above fcHP
fcFb     = min(1 / (2 * ma.PI * Rf * C4), 0.45 * ma.SR);   // 61 kHz to 5.7 kHz

// Diode pair clip level (chosen): small-signal silicon diodes conduct from
// about 0.5 V to 0.7 V. Symmetric, so the distortion is odd-order.
Vd       = 0.6;

// Tone (reported corners, chosen shelf law). The passive low-pass follows the
// clipping stage; the shelf is a behavioural stand-in for the active stage.
fcPassive = 1 / (2 * ma.PI * 1e3 * 220e-9);   // about 723 Hz
fcShelf   = 1 / (2 * ma.PI * 220 * 220e-9);   // about 3.29 kHz
fcZero    = fcShelf * pow(fcPassive / fcShelf, tone);   // 3.29 kHz down to 723 Hz
wShelf    = 2 * ma.PI * fcShelf;
wZero     = 2 * ma.PI * fcZero;

cleanTrim = 0.5;      // Blend 100 % adds a clean path at half amplitude (chosen)
outCeil   = 0.989;    // safety-limiter ceiling, about -0.1 dBFS

//============================================================================
// Driven path.
//============================================================================

// Memoryless diode pair, run inside the oversampler.
diodes = pk.softSat(Vd);

// Feedback branch voltage before the diodes: Rf/R4 times a 720 Hz high-pass
// and the C4 low-pass. The diodes limit it; the op-amp output is the input
// plus the limited branch (Yeh's simplified model).
branch = fi.highpass(1, fcHP) : fi.lowpass(1, fcFb) : *(gainRatio);

clipStage = _ <: @(pk.os4Latency), (branch : pk.oversample4(diodes)) :> _;

// H(s) = (1 + s/wZero) / (1 + s/wShelf): flat at Tone 0, cancels the passive
// low-pass pole at Tone 100.
toneShelf = pk.tf1a(wShelf / wZero, wShelf, wShelf, wShelf);

driven = clipStage
       : fi.lowpass(1, fcPassive)
       : toneShelf
       : fi.dcblockerat(5);

//============================================================================
// Clean path: full-range, delayed to line up with the driven path.
//============================================================================

clean = @(pk.os4Latency) : *(blend * cleanTrim);

mix = _ <: driven, clean :> _;

// Reports the oversampler's delay to the host, which can then compensate it.
latency = pk.os4Latency
        : hbargraph("Latency [unit:samples] [lv2:reportsLatency] [lv2:integer]", 0, 256);

process = fi.highpass(1, fcIn) : mix : *(ba.db2linear(level))
        : pk.safety(outCeil) : attach(_, latency);
