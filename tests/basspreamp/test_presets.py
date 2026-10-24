# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Factory presets (src/basspreamp.presets.toml): each one sets every control
within its range, stays below 0 dBFS, and is loudness-matched to the first
preset ("Clean DI") on a plucked bass line, so switching presets doesn't jump
in level."""

import os
import re

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
src = open(os.path.join(ROOT, "src", "basspreamp.dsp")).read()
controls = {}
for kind, label, args in re.findall(
    r'(hslider|checkbox)\(\s*"\[\d+\]([^\["]+?)\s*[\["][^)]*?"\s*([^)]*)\)', src
):
    if kind == "checkbox":
        controls[label] = (0.0, 1.0)
    else:
        _, lo, hi, _ = (float(a) for a in args.strip(", \n").split(","))
        controls[label] = (lo, hi)


def bass_line():
    """Plucked notes from E1 to G2: band-limited sawtooth (harmonics to 4 kHz)
    with a 2 ms attack, exponential decay and a 10 ms release, peaking at
    -12 dBFS."""
    out = []
    for f in (41.2, 55.0, 73.4, 98.0, 82.4, 41.2, 61.7, 55.0):
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
x = bass_line()
t = np.arange(2 * SR) / SR
square = np.sign(np.sin(2 * np.pi * 41.2 * t))

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
    check(hot_peak <= 0, f"{name}: peak {hot_peak:+.2f} dBFS with a 0 dBFS 41 Hz square in")
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
    title="BassPreamp presets: long-term spectrum of a plucked bass line",
)
ax.grid(True, which="both", alpha=0.3)
ax.legend(fontsize=8)
save_plot(fig, "presets_spectrum")
finish()
