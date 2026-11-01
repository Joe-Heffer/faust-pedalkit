// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// BassTide: a through-zero flanger for bass, with a dry low band and a sweep
// that each note can start for itself. Original design; the reasoning and the
// confidence of every constant are in docs/basstide/design-notes.md.
//
// DRAFT: written without a Faust compiler to hand. It has not been compiled
// or tested yet.
//
// Signal flow (mono):
//
//   in -> DC block -+-> LR4 low-pass (Crossover) -> delay zeroSamples -------------+
//                   |                                                              |
//                   +-> LR4 high-pass -+-> delay zeroSamples x (1 - Depth/2) ------+-> sum
//                   |                  |                                           |
//                   |                  +-> modulated delay tau, with Feedback ------+
//                   |                      x Depth/2
//                   |                         ^ tau = zeroSamples + offset(s)
//                   +-> onset detector -> note sweep --+
//                                                      +-> s = Sweep x mix(LFO, note sweep; Follow)
//                                          LFO (Rate) -+
//   -> Level -> safety limiter -> out
//
// The dry path is delayed by zeroSamples, the through-zero point. The wet
// delay tau can be shorter than that (the wet runs ahead of the dry) or
// longer (it trails it), so the comb sweeps through zero. The host is told
// the dry delay as the plug-in's latency, so the dry signal stays in time.
//
// With Follow at 100 % the sweep only moves when a note starts: the wet
// swings out behind the dry and glides back to the zero point, where wet and
// dry are identical and the comb disappears. A held note ends clean.

declare name        "BassTide";
declare description "Through-zero flanger for bass: each note sweeps out and glides back, above a dry low band";
declare author      "Joe Heffer";
declare license     "MIT";              // SPDX identifier (see tools/fix-ttl.py)
declare version     "0.1.0";
declare lv2class    "FlangerPlugin";
declare homepage    "https://github.com/Joe-Heffer/faust-pedalkit";

import("stdfaust.lib");
pk = library("pedalkit.lib");

//============================================================================
// Controls. Every value is smoothed with si.smoo to avoid zipper noise.
//============================================================================

rate     = hslider("[0]Rate [unit:Hz] [scale:log] [tooltip:Speed of the steady LFO sweep]",
                   0.3, 0.05, 5, 0.01) : si.smoo;
sweep    = hslider("[1]Sweep [unit:%] [tooltip:How far the wet delay moves either side of the zero point]",
                   70, 0, 100, 0.1) / 100 : si.smoo;
follow   = hslider("[2]Follow [unit:%] [tooltip:0 = steady LFO sweep, 100 = each note sweeps out and glides back to the zero point]",
                   100, 0, 100, 0.1) / 100 : si.smoo;
glide    = hslider("[3]Glide [unit:ms] [scale:log] [tooltip:Time scale of the note sweep: how long a note takes to sweep out and come back]",
                   400, 50, 2000, 1) / 1000 : si.smoo;
feedback = hslider("[4]Feedback [unit:%] [tooltip:Negative = hollow, positive = ringing and metallic]",
                   0, -90, 90, 0.1) / 100 : si.smoo;
depth    = hslider("[5]Depth [unit:%] [tooltip:Notch depth. 100 = wet and dry equal, full nulls]",
                   100, 0, 100, 0.1) / 100 : si.smoo;
xover    = hslider("[6]Crossover [unit:Hz] [scale:log] [tooltip:Below this the signal stays dry and unmodulated]",
                   200, 80, 400, 1) : si.smoo;
level    = hslider("[7]Level [unit:dB] [tooltip:Output level]",
                   0, -20, 12, 0.1) : si.smoo;

//============================================================================
// Constants. All chosen; docs/basstide/design-notes.md section 4 gives the
// intent of each.
//============================================================================

// Delay geometry, in samples at the host rate.
zeroSamples = 96;                        // dry delay = through-zero point = reported latency (2 ms at 48 kHz)
minTap      = 2;                         // shortest wet delay; Lagrange interpolation needs at least 1
leadMax     = zeroSamples - minTap;      // furthest the wet runs ahead of the dry: 94 samples
lagMaxSec   = 0.008;                     // furthest the wet trails the dry: 8 ms
lagMax      = lagMaxSec * ma.SR;         // 384 samples at 48 kHz
maxDelay    = 4096;                      // buffer: zeroSamples + 8 ms is 1632 samples at 192 kHz

// Onset detector and note sweep.
fastAtt     = 0.001;   // s: fast envelope attack, follows the pick
fastRel     = 0.010;   // s: fast envelope release, below a low E's half period ripple
slowAtt     = 0.050;   // s: slow envelope attack, lags behind a new note
slowRel     = 0.200;   // s: slow envelope release, follows a note's decay
onsetRatio  = 2;       // an onset is the fast envelope more than 6 dB above the slow one
onsetFloor  = 1e-4;    // -80 dBFS: keeps the ratio finite on silence
levelRef    = 0.1;     // -20 dBFS: a note this loud sweeps about three quarters of the way
holdAtt     = 0.002;   // s: how fast the sweep target jumps up on an onset
glideHold   = 0.5;     // release of the sweep target, as a fraction of Glide
glideSmooth = 0.25;    // smoothing of the sweep itself, as a fraction of Glide
bumpNorm    = 1.7;     // scales the bump so a strong onset reaches the full sweep

// Crossover corner, capped below Nyquist for low host rates (as in BassGrit).
fx       = min(xover, 0.45 * ma.SR);

outCeil  = 0.989;      // safety-limiter ceiling, about -0.1 dBFS

//============================================================================
// Band split: Linkwitz-Riley 4th order, two matched Butterworth sections per
// side, as in BassGrit. The bands sum to an all-pass.
//============================================================================

lowBand  = fi.lowpass(2, fx) : fi.lowpass(2, fx);
highBand = fi.highpass(2, fx) : fi.highpass(2, fx);

//============================================================================
// Sweep position s, from -1 (wet furthest ahead) through 0 (wet = dry) to +1
// (wet furthest behind).
//============================================================================

envFast = abs : si.onePoleSwitching(fastAtt, fastRel);
envSlow = abs : si.onePoleSwitching(slowAtt, slowRel);

// Onset strength, 0 to 1: how far the fast envelope jumps above the slow one,
// times how loud the note is. A sustained or decaying note gives 0.
onset(x) = ma.tanh(max(0, ef - onsetRatio * es) / (es + onsetFloor))
         * ma.tanh(ef / levelRef)
with { ef = x : envFast; es = x : envSlow; };

// Note sweep, 0 to 1: the onset charges a target fast and lets it go over
// glideHold x Glide; a smoother of glideSmooth x Glide turns that into a
// bump that rises, peaks and glides back to 0.
noteSweep(x) = onset(x)
             : si.onePoleSwitching(holdAtt, glide * glideHold)
             : si.smooth(ba.tau2pole(glide * glideSmooth))
             : *(bumpNorm) : min(1);

lfo = os.osc(rate);

position(x) = sweep * ((1 - follow) * lfo + follow * noteSweep(x));

// Offset of the wet delay from the dry, in samples. s x |s| spends more of
// the sweep near zero, where the notches move fastest, and is smooth
// through zero.
offset(s) = s * abs(s) * select2(s < 0, lagMax, leadMax);

tau(x) = zeroSamples + offset(position(x));

//============================================================================
// Wet path: a fractional delay with feedback round it.
//============================================================================

wetPath(h, t) = h : (+ : de.fdelay3(maxDelay, t)) ~ *(feedback);

tide(x) = lo + (1 - mixW) * hiDry + mixW * wetPath(hi, tau(x))
with {
    lo    = x : lowBand : @(zeroSamples);
    hi    = x : highBand;
    hiDry = hi : @(zeroSamples);
    mixW  = depth * 0.5;
};

// Reports the dry path's delay to the host, which can then compensate it.
latency = zeroSamples
        : hbargraph("Latency [unit:samples] [lv2:reportsLatency] [lv2:integer]", 0, 256);

process = fi.dcblockerat(5) : tide : *(ba.db2linear(level))
        : pk.safety(outCeil) : attach(_, latency);
