# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Factory presets (src/midhump.presets.toml): each one sets every control
within its range, stays below 0 dBFS, and is loudness-matched to the first
preset ("Edge of Breakup") on a plucked guitar line, so switching presets
doesn't jump in level. Also checks that presets.h, which carries the presets into the VST3
and CLAP plugins, holds each preset's values in parameter order."""

import os
import re
import subprocess
import sys

import numpy as np

from fxtest import (
    OUT,
    ROOT,
    SR,
    check,
    db,
    finish,
    loudness,
    plt,
    presets,
    render,
    save_plot,
    write_csv,
    write_wav,
)

print("test_presets")
MATCH_DB = 1.0  # allowed loudness difference from the reference preset

# Controls declared in the DSP: label -> (minimum, maximum). Checkboxes are 0/1.
src = open(os.path.join(ROOT, "src", "midhump.dsp")).read()
controls = {}
for kind, label, args in re.findall(
    r'(hslider|checkbox)\(\s*"\[\d+\]([^\["]+?)\s*[\["][^)]*?"\s*([^)]*)\)', src
):
    if kind == "checkbox":
        controls[label] = (0.0, 1.0)
    else:
        _, lo, hi, _ = (float(a) for a in args.strip(", \n").split(","))
        controls[label] = (lo, hi)
# Parameter order: the [n] prefixes, which the VST3 and CLAP parameter IDs follow.
order = [
    label
    for _, label in sorted(
        (int(n), label)
        for n, label in re.findall(r'(?:hslider|checkbox)\(\s*"\[(\d+)\]([^\["]+?)\s*[\["]', src)
    )
]


def guitar_line():
    """Plucked notes from E2 to E4: band-limited sawtooth (harmonics to 4 kHz)
    with a 2 ms attack, exponential decay and a 10 ms release, peaking at
    -12 dBFS."""
    out = []
    for f in (82.4, 110.0, 146.8, 196.0, 246.9, 329.6, 196.0, 82.4):
        t = np.arange(SR // 2) / SR
        x = sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, int(4000 / f)))
        out.append(
            x * np.exp(-4 * t) * np.minimum(1, t / 0.002) * np.minimum(1, (t[-1] - t) / 0.01)
        )
    x = np.concatenate(out)
    return x / np.max(np.abs(x)) * 10 ** (-12 / 20)


def third_octaves(y):
    """Energy in third-octave bands from 25 Hz to 16 kHz, in dB."""
    spec = np.abs(np.fft.rfft(y)) ** 2
    f = np.fft.rfftfreq(len(y), 1 / SR)
    centres = 1000 * 2 ** (np.arange(-16, 13) / 3)
    bands = [spec[(f >= c * 2 ** (-1 / 6)) & (f < c * 2 ** (1 / 6))].sum() for c in centres]
    return centres, 10 * np.log10(np.array(bands) / len(y) ** 2 + 1e-30)


P = presets()
check(len(P) > 0, f"{len(P)} presets found")
x = guitar_line()
t = np.arange(2 * SR) / SR
square = np.sign(np.sin(2 * np.pi * 82.4 * t))

rows, spectra, ref = [], [], None
for name, ctl in P:
    missing = controls.keys() - ctl.keys()
    unknown = ctl.keys() - controls.keys()
    out_of_range = [
        k for k, v in ctl.items() if k in controls and not controls[k][0] <= v <= controls[k][1]
    ]
    check(not (missing or unknown or out_of_range), f"{name}: sets every control within range")
    if missing or unknown:
        continue

    y = render(x, **ctl)
    hot = render(square, **ctl)
    L = loudness(y)
    ref = L if ref is None else ref
    peak, hot_peak = db(np.max(np.abs(y))), db(np.max(np.abs(hot)))
    check(np.all(np.isfinite(y)) and np.all(np.isfinite(hot)), f"{name}: output is finite")
    check(hot_peak <= 0, f"{name}: peak {hot_peak:+.2f} dBFS with a 0 dBFS 82 Hz square in")
    check(
        abs(L - ref) <= MATCH_DB,
        f"{name}: loudness {L - ref:+.2f} dB from the reference (±{MATCH_DB:g})",
    )
    rows.append((name, L - ref, peak, hot_peak))
    spectra.append((name, *third_octaves(y)))
    write_wav(os.path.join(OUT, "preset-" + re.sub(r"[^a-z0-9]+", "-", name.lower()) + ".wav"), y)

write_csv("presets_levels", ["preset", "loudness_rel_db", "peak_dbfs", "square_peak_dbfs"], rows)
write_csv(
    "presets_spectrum",
    ["preset", "band_hz", "level_db"],
    [(n, c, v) for n, cs, vs in spectra for c, v in zip(cs, vs, strict=True)],
)

fig, ax = plt.subplots(figsize=(9, 5))
for name, cs, vs in spectra:
    ax.semilogx(cs, vs, marker=".", label=name)
ax.set(
    xlabel="Third-octave band (Hz)",
    ylabel="Level (dB)",
    title="MidHump presets: long-term spectrum of a plucked guitar line",
)
ax.grid(True, which="both", alpha=0.3)
ax.legend(fontsize=8)
save_plot(fig, "presets_spectrum")

# presets.h: generate it as the VST3 and CLAP builds do, and compare it with
# the TOML in the order of the [n] prefixes. Copies already built into
# build/midhump/{vst3,clap}/ must be identical to it.
header = os.path.join(OUT, "presets.h")
subprocess.run(
    [
        sys.executable,
        "tools/presets.py",
        "header",
        "src/midhump.presets.toml",
        "build/midhump/controls.json",
        header,
    ],
    cwd=ROOT,
    check=True,
)
text = open(header).read()
entries = re.findall(r'^    \{"((?:[^"\\]|\\.)*)", "(?:[^"\\]|\\.)*", \{([^}]*)\}\},$', text, re.M)
check(len(entries) == len(P), f"presets.h holds {len(entries)} of {len(P)} presets")
for (name, ctl), (hname, values) in zip(P, entries, strict=False):
    got = [float(v.strip().rstrip("f")) for v in values.split(",")]
    want = [float(ctl[label]) for label in order]
    check(hname == name and got == want, f"presets.h: {name} in parameter order")
for fmt in ("vst3", "clap"):
    built = os.path.join(ROOT, "build", "midhump", fmt, "presets.h")
    if os.path.exists(built):
        check(open(built).read() == text, f"build/midhump/{fmt}/presets.h is up to date")
    else:
        print(f"  (no {fmt} build to compare: run make {fmt})")
finish()
