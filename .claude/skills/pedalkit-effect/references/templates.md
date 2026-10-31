# Templates for a new effect

Copy and adapt these. Replace `<name>` and the placeholders, and keep British English.

## Design notes: `docs/<name>/design-notes.md`

```markdown
# <Name>: design notes

## 1. The idea

What it should sound like, in words and in measurable terms. What a player gets that existing effects don't give them.

## 2. Prior art and inspirations

What is borrowed and what is new. Each source is numbered and linked ([1], [2], …).

## 3. Block diagram

The signal flow. Mark each block as new, from `pedalkit.lib`, or from another effect.

## 4. Constants

| Constant | Value | Confidence | Intent / source |
|---|---|---|---|
| `preHz` | 800 | Chosen | Centre of the band the effect acts on; retune by ear |

Confidence is one of Documented, Reported, Inferred or Chosen.

## 5. Measurable targets

What the tests check to show the idea works, for example “H2 rises above H3 as Drive passes noon”.

## 6. Dynamics and feel

How it responds to picking strength and over the life of a note: the cleanup curve, attack against sustain, what a loud passage leaves behind. State each as a target, for example “THD rises from 1 % to 10 % over at least 18 dB of input”. Mechanisms and measurements are in `docs/development/designing-for-feel.md`.

## 7. Open questions

Especially those only listening can answer.

## Sources

1. Title, author, [link](https://example.org).
```

## DSP skeleton: `src/<name>.dsp`

```faust
// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// <Name>: one-line description. Reasoning in docs/<name>/design-notes.md.
//
// Signal flow (mono):
//
//   in -> DC block -+-> delay (latency match) -----+
//                   |                              +-> Mix -> Level -> safety -> out
//                   +-> filter -> 4x OS shaper -----+

declare name        "<Name>";
declare description "<One line>";
declare author      "Joe Heffer";
declare license     "MIT";
declare version     "0.1.0";
declare lv2class    "DistortionPlugin";
declare homepage    "https://github.com/Joe-Heffer/faust-pedalkit";

import("stdfaust.lib");
pk = library("pedalkit.lib");

// Controls. Every value is smoothed.
level = hslider("[0]Level [unit:dB] [tooltip:Output level]", 0, -40, 12, 0.1) : si.smoo;
mix   = hslider("[1]Mix [unit:%] [tooltip:0 = dry, 100 = effect]", 50, 0, 100, 0.1) / 100 : si.smoo;
drive = hslider("[2]Drive [unit:%] [tooltip:Amount of drive]", 30, 0, 100, 0.1) / 100 : si.smoo;

// Constants: say where each came from or what it is for.
preHz   = 800;    // filter corner (chosen: centre of the band to push)
driveDB = 30;     // gain at full Drive (chosen)
outCeil = 0.989;  // safety-limiter ceiling, about -0.1 dBFS

// Memoryless shaper only: it runs on four parallel phase streams.
shaper(x) = pk.softSat(1.0, x * ba.db2linear(drive * driveDB));

// A stage with memory (bias shift, sag) splits into a base-rate control and a
// memoryless shaper f(x, c), e.g. (constants from designing-for-feel.md):
//   clip  = pk.biased(pk.softSat(0.6));
//   bias  = pk.biasShift(0.6, 0.3, 0.015, 0.15);
//   stage = _ <: _, bias : pk.oversample4c(clip);

wet = fi.highpass(1, preHz) : pk.oversample4(shaper) : fi.dcblockerat(5);
dry = @(pk.os4Latency);

blend = _ <: dry, wet : *(1 - mix), *(mix) :> _;

latency = pk.os4Latency
        : hbargraph("Latency [unit:samples] [lv2:reportsLatency] [lv2:integer]", 0, 256);

process = fi.dcblockerat(5) : blend : *(ba.db2linear(level))
        : pk.safety(outCeil) : attach(_, latency);
```

`src/lib/pedalkit.lib` is the source of truth for helper signatures (for example `softSat(v, x)` and `safety(lim, x)`). Check it before relying on this skeleton.

## Test skeleton: `tests/<name>/test_silence.py`

```python
# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Silence in must give silence out, at every extreme setting."""

import itertools

import numpy as np

from fxtest import SR, check, db, finish, render

print("test_silence")
x = np.zeros(3 * SR)
for drive, level, mix in itertools.product((0, 100), (-40, 12), (0, 50, 100)):
    y = render(x, Drive=drive, Level=level, Mix=mix)
    peak = np.max(np.abs(y)) if len(y) else 0.0
    if peak > 1e-6 or not np.all(np.isfinite(y)):
        check(False, f"silence D={drive} L={level} M={mix}: peak {db(peak):.1f} dBFS")
        break
else:
    check(True, "silence in gives < -120 dBFS out at 12 setting combinations")
finish()
```

Controls are addressed by their label as written in the `hslider`, without the `[n]` prefix or the bracketed tags.

Other tests to copy from `tests/bassdrive/`: `test_peak.py`, `test_freqresp.py`, `test_harmonics.py` (includes the aliasing comparison), `test_sweep.py` and `test_samplerates.py`. For targets and dynamics, copy from `tests/midhump/`: `test_targets.py` and `test_dynamics.py`.

## Changelog: `docs/<name>/changelog.md`

Copy `docs/bassdrive/changelog.md` and keep a `## [0.1.0]` section.

## Pull request

Use `.github/pull_request_template.md`. Add the `new-effect` and `effect: <name>` labels if you can (create the effect label if it doesn't exist yet).
