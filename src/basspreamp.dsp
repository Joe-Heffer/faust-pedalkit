// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// BassPreamp: a tube-voiced bass preamp and DI with clean blend, Presence and
// three-band EQ with switchable Bass and Mid frequencies.
//
// Modelled on a well-known bass preamp/DI pedal, using only public sources:
// a DIY schematic trace of the earlier version's drive section, plus the
// manufacturer's and reviewers' specifications of the current version's EQ.
// See docs/basspreamp/circuit-notes.md for the sources and for which values
// are documented, reported, inferred or chosen.
//
// Signal flow (mono):
//
//   in -> DC block -+-> delay (latency match) ------------------------------+
//                   |                                                       +-> Blend
//                   +-> pre-drive network (bass-weighted, scooped treble)   |  (C16 into
//                       -> Presence stage (HF boost) -> 4x OS rail clip     |   the pot)
//                       -> Drive stage (gain)       -> 4x OS rail clip     |
//                       -> divider + Sallen-Key low-pass with shelf leg     |
//                       -> Sallen-Key low-pass -> bridged-T notch -> trim --+
//                          (the speaker voicing; Cab Bypass skips it)
//   -> Bass (shelf, 80/40 Hz) -> Mid (peak, 500 Hz/1 kHz) -> Treble (shelf)
//   -> Level -> safety limiter -> out
//
// The "speaker voicing" is the fixed post-clip filtering of the driven path.
// It is always on in the hardware; Cab Bypass (not on the hardware) removes
// it, for use with a real cabinet or an impulse response. The clean path stays
// full-range either way.
//
// Levels: 1.0 full scale is treated as 1 V peak at the circuit input.

declare name        "BassPreamp";
declare description "Tube-voiced bass preamp/DI with blend, presence and three-band EQ";
declare author      "Joe Heffer";
declare license     "MIT";              // SPDX identifier (see tools/fix-ttl.py)
declare version     "0.2.0";
declare lv2class    "AmplifierPlugin";
declare homepage    "https://github.com/Joe-Heffer/faust-pedalkit";

import("stdfaust.lib");
pk = library("pedalkit.lib");

//============================================================================
// Controls. Every value is smoothed with si.smoo to avoid zipper noise.
//============================================================================

level    = hslider("[0]Level [unit:dB] [tooltip:Output level]",
                   0, -40, 12, 0.1) : si.smoo;
blend    = hslider("[1]Blend [unit:%] [tooltip:0 = clean only, 100 = preamp only]",
                   50, 0, 100, 0.1) / 100 : si.smoo;
drive    = hslider("[2]Drive [unit:%] [tooltip:Amount of overdrive]",
                   50, 0, 100, 0.1) / 100 : si.smoo;
presence = hslider("[3]Presence [unit:%] [tooltip:Upper harmonics and attack in the preamp path]",
                   50, 0, 100, 0.1) / 100 : si.smoo;
bass     = hslider("[4]Bass [unit:dB] [tooltip:Low shelf at 80 Hz, or 40 Hz with Bass Shift]",
                   0, -12, 12, 0.1) : si.smoo;
mid      = hslider("[5]Mid [unit:dB] [tooltip:Mid band at 500 Hz, or 1 kHz with Mid Shift]",
                   0, -12, 12, 0.1) : si.smoo;
treble   = hslider("[6]Treble [unit:dB] [tooltip:High shelf]",
                   0, -12, 12, 0.1) : si.smoo;
bassSh   = checkbox("[7]Bass Shift [tooltip:Off = 80 Hz, on = 40 Hz]") : si.smoo;
midSh    = checkbox("[8]Mid Shift [tooltip:Off = 500 Hz, on = 1 kHz]") : si.smoo;
// Appended last so the VST3 and CLAP parameter IDs of existing projects stay
// valid. A checkbox defaults to off, so the default keeps the voicing on.
cabByp   = checkbox("[9]Cab Bypass [tooltip:Off = speaker voicing on the preamp path, as on the hardware; on = preamp path unfiltered, for a cabinet or impulse response]") : si.smoo;

//============================================================================
// Circuit constants (see circuit-notes.md, sections 3 to 8).
//============================================================================

// Presence stage (IC2_C): non-inverting, R7 || C6 in feedback, C7 + R8 + pot
// to VB (all reported, DIY trace [2]).
R7       = 330e3;
C6       = 220e-12;
C7       = 10e-9;
R8       = 3.3e3;
RpresPot = 100e3;     // 100 kOhm linear pot wired as a rheostat (reported)

// Drive stage (IC2_D): non-inverting, R9 || C8 in feedback, R10 + pot to VB
// (reported). No capacitor in the ground leg, so the gain reaches DC.
R9       = 330e3;
C8       = 220e-12;
R10      = 3.3e3;
RdrivePot = 100e3;    // 100 kOhm linear pot wired as a rheostat (reported)

// Control laws (chosen). The traced linear pots bunch the useful range into
// the last 10-20 % of rotation; here each control sweeps the same resistance
// range log-uniformly, so equal steps give equal changes in dB.
RgPres   = (R8 + RpresPot) * pow(R8 / (R8 + RpresPot), presence);
driveG   = 1 + R9 / ((R10 + RdrivePot) * pow(R10 / (R10 + RdrivePot), drive));

// Op-amp rails: TL07x on a ~9.3 V supply swings to ~1.5 V from each rail, so
// about +/-3.1 V around VB (inferred from datasheet typicals and the
// published test voltages). The knee hardness is chosen.
railV    = 3.1;
railN    = 5;
vos      = 0.002;     // input offset voltage of the drive op-amp (chosen; TL07x typ. 3 mV)

fcBlend  = 1 / (2 * ma.PI * 47e-9 * 100e3);   // C16 into the 100 k Blend pot, ~34 Hz (reported values)
drvTrim  = 0.32;      // driven = clean level at Drive/Presence 50 % (chosen, measured)
bypTrim  = 0.28;      // -11 dB in place of the voicing with Cab Bypass on: loudness-matched to the
                      // voiced path at Drive/Presence 50 % (chosen, measured; 5-11 dB elsewhere)

// V2 EQ (documented: +/-12 dB, 40/80 Hz and 500/1000 Hz). Shapes are chosen.
bassF    = 80 * pow(0.5, bassSh);     // smoothed switch glides 80 -> 40 Hz
midF     = 500 * pow(2, midSh);       // 500 Hz -> 1 kHz
midQ     = 0.7;                       // chosen
trebF    = 2800;                      // inferred from the earlier version's Baxandall values

outCeil  = 0.989;     // safety-limiter ceiling, about -0.1 dBFS

//============================================================================
// Fixed networks. These coefficients are generated by
// tools/basspreamp-networks.py from the traced component values (nodal
// analysis, ideal op-amps); rerun it if a value changes. Each section is an
// analogue transfer function discretised with the bilinear transform.
//============================================================================

// R3 100k bridged by C2/C3/C4 22n with R4 2k2 and R5 22k to VB, then C5 22n
// into R6 100k. Peak -10 dB around 70 Hz, falling to -25 dB above 3 kHz.
preNet = pk.tf2a(0.04874446086, 49.03343581, 0, 909.9396802, 125203.6712, 353.841308)
    : pk.tf1a(1, 14145.58679, 2518.103339, 2518.103339);

// R11 10k / R12 22k divider, then a Sallen-Key low-pass (R13, R15 22k, C9
// 10n, C11 470p) with a shelf leg (R14 10k + C10 47n): low shelf of about
// -10 dB from 90 to 340 Hz and a resonance near 5.8 kHz (Q 1.85).
postSK1 = pk.tf2a(0, 230266187.7, 4.89928059e+11, 19591.67388, 1308419841, 36172.08649)
    : pk.tf1a(0, 1, 544.643706, 544.643706);

// Sallen-Key low-pass: R16, R17 33k, C12 2n2, C13 1n2. 2.97 kHz, Q 0.68.
postSK2 = pk.tf2a(0, 0, 347830926.3, 27548.20937, 347830926.3, 18650.22591);

// Bridged-T notch: R18 22k bridged by C14 22n / C15 47n with R19 6k2 to VB.
// About -11 dB at 424 Hz.
postNotch = pk.tf2a(1, 3033.233691, 7090307.833, 10364.61199, 7090307.833, 2662.763195);

//============================================================================
// Driven path.
//============================================================================

// Non-inverting stage with Zf = R7 || C6 and Zg = R + 1/sC (presence):
//   H = 1 + Zf/Zg
//     = (1 + s(R7C6 + RC7 + R7C7) + s^2 R7C6RC7) / (1 + s(R7C6 + RC7) + s^2 R7C6RC7)
// Unity at low frequencies, a boost of up to ~30 dB around 3-5 kHz.
presStage = pk.tf2a(1, (R7*C6 + RgPres*C7 + R7*C7) / k, 1 / k,
                       (R7*C6 + RgPres*C7) / k, 1 / k, 2 * ma.PI * 3000)
with { k = R7 * C6 * RgPres * C7; };

// Non-inverting stage with Zf = R9 || C8 and a resistive ground leg (drive):
//   H = 1 + (G - 1) / (1 + s R9 C8),   G = 1 + R9/Rg from about 4.2 to 101
driveStage = pk.tf1a(1, driveG / (R9 * C8), 1 / (R9 * C8), 2 * ma.PI * 2000);

// Op-amp running into its rails: memoryless, so it can sit inside the
// oversampler. The drive stage's offset (vos times its DC gain) is added
// before the clip, which skews the clipping more as Drive rises.
rail = pk.kneeClip(railV, railN);

// The speaker voicing, or with Cab Bypass a plain trim in its place. The
// smoothed switch crossfades between the two, so toggling doesn't click.
voicing = _ <: (postSK1 : postSK2 : postNotch), *(bypTrim)
        : si.interpolate(cabByp);

driven = preNet
       : presStage : pk.oversample4(rail)
       : driveStage : +(vos * driveG) : pk.oversample4(rail)
       : voicing
       : *(drvTrim);

//============================================================================
// Clean path: full-range, only delayed to line up with the driven path.
//============================================================================

latencySamples = 2 * pk.os4Latency;

clean = @(latencySamples);

//============================================================================
// Blend, EQ and output.
//============================================================================

// The driven signal reaches the Blend pot through C16, the clean signal is
// tied to the pot's other end. The wiper therefore sees
//   clean + b * HP(driven - clean)
// with a first-order high-pass at fcBlend: below ~34 Hz the clean signal
// passes whatever the Blend setting, and the clipper's DC offset is removed.
mix = _ <: clean, driven : (_ <: _, _), _ : _, (- : *(-1) : fi.highpass(1, fcBlend) : *(blend)) :> _;

tone = fi.low_shelf(bass, bassF)
     : fi.peak_eq_cq(mid, midF, midQ)
     : fi.high_shelf(treble, trebF);

// Reports the oversamplers' delay to the host, which can then compensate it.
latency = latencySamples
        : hbargraph("Latency [unit:samples] [lv2:reportsLatency] [lv2:integer]", 0, 256);

process = fi.dcblockerat(5) : mix : tone : *(ba.db2linear(level))
        : pk.safety(outCeil) : attach(_, latency);
