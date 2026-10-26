// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// BassGrit: a hard-clipping distortion in the style of a well-known op-amp
// distortion pedal, split so the low end stays clean. Circuit-inspired:
// docs/bassgrit/circuit-notes.md (borrowed part) and design-notes.md (departures).
//
// Signal flow (mono):
//
//   in -> DC block -+-> 4th-order LP (Crossover) -> delay (latency match) -> x Blend --+
//                   |                                                                 |
//                   +-> 4th-order HP (Crossover) -+-> (input) ---+                     |
//                                                 |             +-> op-amp output      |
//                                                 +-> branch ---+   (input + branch)   |
//                                                     (two grounded legs, feedback     |
//                                                      pole, gain-bandwidth pole)      |
//   -> 4x OS hard diode pair -> Filter low-pass -> (driven) -> driven plus clean low ----+
//   -> Level -> safety limiter -> out
//
// The split is Linkwitz-Riley 4th order (two matched Butterworth sections per
// side): the bands are in phase at the crossover, so they sum to an all-pass
// when nothing is clipped, and each side falls at 24 dB/octave so a low-note
// fundamental barely reaches the clipper.
//
// Levels: 1.0 full scale is treated as 1 V peak at the circuit input.

declare name        "BassGrit";
declare description "Hard-clipping distortion with a clean low band, for bass";
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

dist  = hslider("[0]Distortion [unit:%] [tooltip:Gain of the op-amp stage]",
                50, 0, 100, 0.1) / 100 : si.smoo;
filt  = hslider("[1]Filter [unit:%] [tooltip:0 = bright, 100 = dark (as on the pedal it follows)]",
                30, 0, 100, 0.1) / 100 : si.smoo;
level = hslider("[2]Level [unit:dB] [tooltip:Output level]",
                0, -40, 12, 0.1) : si.smoo;
blend = hslider("[3]Low Blend [unit:%] [tooltip:Clean signal below the crossover. 0 = fully distorted]",
                70, 0, 100, 0.1) / 100 : si.smoo;
xover = hslider("[4]Crossover [unit:Hz] [tooltip:Below this the signal bypasses the clipper]",
                120, 40, 400, 1) : si.smoo;

//============================================================================
// Constants (confidence of each is in the notes: reported, inferred or chosen).
//============================================================================

// Gain stage (reported): non-inverting, gain 1 + Zf/Zg. The grounded side is
// two RC legs in parallel; the feedback side is a pot in parallel with a cap.
RA       = 47;        // leg A resistor
CA       = 2.2e-6;    // leg A capacitor, corner about 1.54 kHz
RB       = 560;       // leg B resistor
CB       = 4.7e-6;    // leg B capacitor, corner about 60 Hz
Rpot     = 100e3;     // Distortion pot
Cf       = 100e-12;   // feedback capacitor
// Gain-bandwidth product of the op-amp with its compensation capacitor
// (inferred: of the order of 1 MHz; the real part varies between samples).
GBW      = 1e6;
// Corners are capped at 0.45 SR: fi.highpass/fi.lowpass go unstable above
// Nyquist, which only matters at very low host sample rates.
fcA      = min(1 / (2 * ma.PI * RA * CA), 0.45 * ma.SR);
fcB      = min(1 / (2 * ma.PI * RB * CB), 0.45 * ma.SR);

// Distortion pot law (chosen): log taper, about 9 % of the pot at noon.
Rf       = Rpot * (pow(10, 2 * dist) - 1) / 99;
// Closed-loop bandwidth: GBW over the high-frequency gain, where the two legs
// are in parallel (47 || 560).
gainHF   = 1 + Rf / (RA * RB / (RA + RB));
fcFb     = min(1 / (2 * ma.PI * max(Rf, 1) * Cf), 0.45 * ma.SR);
fcGbw    = min(GBW / gainHF, 0.45 * ma.SR);

// Diode pair after a series resistor (reported: silicon switching diodes).
// kneeClip is a hard but not perfect knee; Vd is where it limits (chosen).
Vd       = 0.6;
nKnee    = 4;         // knee hardness (chosen: harder than tanh, softer than a clamp)

// Filter (reported corners, chosen capacitor): series 1.5 kOhm + pot into a
// capacitor to ground. The pedal uses 3.3 nF (475 Hz to 32 kHz); 4.7 nF moves
// the range down to about 340 Hz to 22 kHz (chosen, for bass).
Rs       = 1.5e3;
RfiltPot = 100e3;
Cfilt    = 4.7e-9;
Rfilt    = RfiltPot * (pow(10, 2 * filt) - 1) / 99;      // log taper (chosen)
fcFilt   = min(1 / (2 * ma.PI * (Rs + Rfilt) * Cfilt), 0.45 * ma.SR);

outTrim  = 1.2;       // restores level lost to the 0.6 V clip, applied to both bands (chosen)
outCeil  = 0.989;     // safety-limiter ceiling, about -0.1 dBFS

//============================================================================
// Band split: Linkwitz-Riley 4th order, two matched Butterworth sections.
//============================================================================

fx       = min(xover, 0.45 * ma.SR);
lowBand  = fi.lowpass(2, fx) : fi.lowpass(2, fx);
highBand = fi.highpass(2, fx) : fi.highpass(2, fx);

//============================================================================
// Driven path.
//============================================================================

// Memoryless hard-ish diode pair, run inside the oversampler.
diodes = pk.kneeClip(Vd, nKnee);

// Op-amp output = input + (Zf/Zg) x input. Each grounded leg is a first-order
// high-pass scaled by Rf over its resistor; the feedback cap and the
// gain-bandwidth limit add two low-pass poles.
branch = _ <: (fi.highpass(1, fcA) : *(Rf / RA)),
              (fi.highpass(1, fcB) : *(Rf / RB)) :> _
       : fi.lowpass(1, fcFb) : fi.lowpass(1, fcGbw);

opamp = _ <: _, branch :> _;

driven = highBand : opamp : pk.oversample4(diodes)
       : fi.lowpass(1, fcFilt);

//============================================================================
// Clean low band, delayed to line up with the driven path.
//============================================================================

clean = lowBand : @(pk.os4Latency) : *(blend);

mix = _ <: driven, clean :> _;

// Reports the oversampler's delay to the host, which can then compensate it.
latency = pk.os4Latency
        : hbargraph("Latency [unit:samples] [lv2:reportsLatency] [lv2:integer]", 0, 256);

process = fi.dcblockerat(5) : mix : *(outTrim * ba.db2linear(level))
        : pk.safety(outCeil) : attach(_, latency);
