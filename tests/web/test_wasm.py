# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Browser build: the WebAssembly from `make web` against the native build.

Run with `make web-test`. For each effect in WEB_FX, tools/web/render.mjs runs
build/web/<name>/dsp-module.wasm in Node through faustwasm, the same runtime
the demo page uses, and this script checks:

* silence in gives silence out
* the peak stays at or below 0 dBFS with every control at its maximum, and at
  its minimum, on a full-scale input
* the output matches the native renderer (build/<name>/render) at the
  default, maximum and minimum settings, on a sine and a sweep
* the WebAssembly runs fast enough for an AudioWorklet

The two builds come from different Faust compilers (the system Faust for the
native renderer, faustwasm's bundled libfaust for the browser), so they can
use slightly different library versions; MATCH_DB allows for that.

Results: tests/out/web/wasm_vs_native.csv and tests/out/web/realtime.csv.
"""

import json
import os
import subprocess

import numpy as np

from fxtest import ROOT, SR, check, db, finish, log_sweep, render, sine, write_csv

NODE = os.environ.get("NODE", "node")
EFFECTS = os.environ.get("WEB_FX", "").split()
RENDER_WASM = os.path.join(ROOT, "tools", "web", "render.mjs")

# Chosen: the difference between the two builds, relative to the native
# output's RMS. -60 dB is far below anything audible in an A/B, while still
# catching a wrong control mapping, a missing stage or a sample-rate error.
MATCH_DB = -60.0
# Chosen: silence must stay below this level (no DC offset, no noise source).
SILENCE_DB = -120.0
# Chosen: seconds of audio processed per second of compute, in Node. The
# AudioWorklet must finish each 128-sample block within its 2.7 ms at 48 kHz.
# Anything above 1 keeps up; 2 leaves room for a slow CI runner and catches a
# change that makes an effect several times more expensive. It says nothing
# about the slowest phone a visitor might use (see docs/usage/browser.md).
MIN_REALTIME = 2.0


def render_wasm(name, x, **params):
    """Process x with the browser build; returns (output, realtime factor)."""
    args = [NODE, RENDER_WASM, os.path.join(ROOT, "build", "web", name), str(SR)]
    args += [f"{k}={v}" for k, v in params.items()]
    res = subprocess.run(
        args, input=np.asarray(x, dtype=np.float32).tobytes(), capture_output=True, check=True
    )
    factor = float(res.stderr.decode().split("realtime")[-1])
    return np.frombuffer(res.stdout, dtype=np.float32).astype(np.float64), factor


def controls(name):
    """Sliders and checkboxes from the effect's dsp-meta.json, by label."""
    with open(os.path.join(ROOT, "build", "web", name, "dsp-meta.json")) as f:
        meta = json.load(f)
    found = []

    def walk(items):
        for item in items:
            if "items" in item:
                walk(item["items"])
            elif item["type"] in ("hslider", "vslider", "nentry"):
                found.append((item["label"], item["min"], item["max"]))
            elif item["type"] in ("checkbox", "button"):
                found.append((item["label"], 0, 1))

    walk(meta["ui"])
    return found


def rms_db(x):
    return 10 * np.log10(np.mean(np.square(x)) + 1e-30)


match_rows = []
speed_rows = []
check(bool(EFFECTS), f"effects to test: {' '.join(EFFECTS) or 'none (set WEB_FX)'}")

for name in EFFECTS:
    print(f"== {name}")
    native = os.path.join(ROOT, "build", name, "render")
    ctl = controls(name)
    settings = {
        "default": {},
        "max": {label: hi for label, _, hi in ctl},
        "min": {label: lo for label, lo, _ in ctl},
    }

    y, _ = render_wasm(name, np.zeros(SR))
    check(db(np.max(np.abs(y))) <= SILENCE_DB, f"{name}: silence in gives silence out")

    loud = sine(50, 2.0, amp_db=0.0)
    for setting in ("max", "min"):
        y, _ = render_wasm(name, loud, **settings[setting])
        peak = db(np.max(np.abs(y)))
        check(peak <= 0.0, f"{name}: peak {peak:.2f} dBFS <= 0 at {setting} settings, 0 dBFS input")

    signals = {"sine 110 Hz": sine(110, 2.0), "sweep 20 Hz-20 kHz": log_sweep(20, 20000, 4.0)[0]}
    for setting, params in settings.items():
        for signal, x in signals.items():
            ref = render(x, binary=native, **params)
            y, factor = render_wasm(name, x, **params)
            err = rms_db(y - ref) - rms_db(ref)
            check(err <= MATCH_DB, f"{name}: {setting}, {signal}: wasm - native = {err:.1f} dB")
            match_rows.append((name, setting, signal, err))
            speed_rows.append((name, setting, signal, factor))

    slowest = min(f for n, *_, f in speed_rows if n == name)
    check(slowest >= MIN_REALTIME, f"{name}: runs at {slowest:.1f}x real time (>= {MIN_REALTIME}x)")

write_csv("wasm_vs_native", ["effect", "setting", "signal", "difference_db"], match_rows)
write_csv("realtime", ["effect", "setting", "signal", "realtime_factor"], speed_rows)
finish()
