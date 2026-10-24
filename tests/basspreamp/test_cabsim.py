# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Cab Bypass: the speaker voicing on and off.

With the voicing bypassed the preamp path keeps more treble (no steep roll-off
above 5 kHz) and loses the voicing's bass hump, it is loudness-matched to the voiced path
at the default Drive and Presence, and the clean path is unaffected.
"""

import numpy as np

from fxtest import SR, check, db, finish, loudness, plt, render, save_plot, transfer, write_csv

print("test_cabsim")
rng = np.random.default_rng(11)
noise = rng.normal(0, 1, 8 * SR)
CAB = "Cab Bypass"
rows = []


def at(f, H, hz):
    return db(np.abs(H[np.argmin(np.abs(f - hz))]))


def bass_line():
    """Plucked notes from E1 to G2, as in test_presets.py, peaking at -12 dBFS."""
    out = []
    for f in (41.2, 55.0, 73.4, 98.0, 82.4, 41.2, 61.7, 55.0):
        t = np.arange(SR // 2) / SR
        x = sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, int(4000 / f)))
        out.append(
            x * np.exp(-4 * t) * np.minimum(1, t / 0.002) * np.minimum(1, (t[-1] - t) / 0.01)
        )
    x = np.concatenate(out)
    return x / np.max(np.abs(x)) * 10 ** (-12 / 20)


fig, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)

# Small-signal response of the preamp path, voiced and bypassed.
ax = axes[0]
curves = {}
for lvl in (-70, -20):
    for cab in (0, 1):
        x = noise * 10 ** (lvl / 20)
        f, H = transfer(x, render(x, Blend=100, **{CAB: cab}))
        curves[lvl, cab] = (f, H)
        label = f"{'bypassed' if cab else 'voiced'}, {lvl} dBFS"
        ax.semilogx(f[1:], db(H[1:]), "--" if lvl == -20 else "-", label=label)
        idx = np.unique(
            np.geomspace(np.searchsorted(f, 20), np.searchsorted(f, 20000), 200).astype(int)
        )
        rows.extend((lvl, cab, f[i], db(H[i])) for i in idx)
ax.set_title("Preamp path (Blend 100 %, Drive and Presence 50 %)")
ax.set_xlim(20, 20000)
ax.set_ylim(-50, 30)
ax.set_xlabel("frequency (Hz)")
ax.set_ylabel("gain (dB)")
ax.grid(True, which="both", alpha=0.3)
ax.legend(fontsize=8)

# Without the voicing the path is still dark: the pre-drive network and the
# drive stage's R9 || C8 pole roll it off above a few kHz. So the checks are
# relative to the voiced path.
f, Hv = curves[-70, 0]
_, Hb = curves[-70, 1]
hv, hb = (at(f, H, 12000) - np.max(db(H[(f > 100) & (f < 5000)])) for H in (Hv, Hb))
check(hv < -20, f"voiced: 12 kHz is {hv:.1f} dB below the peak (< -20 dB)")
check(hb - hv > 15, f"bypassed: 12 kHz is {hb:.1f} dB below the peak, {hb - hv:.1f} dB less (> 15)")
lift = (at(f, Hb, 8000) - at(f, Hb, 1000)) - (at(f, Hv, 8000) - at(f, Hv, 1000))
check(lift > 8, f"bypass keeps {lift:.1f} dB more 8 kHz relative to 1 kHz (> 8 dB)")

# Loudness match at the defaults, reported across Drive.
x = bass_line()
ax = axes[1]
drives = (0, 25, 50, 75, 100)
diffs = []
for d in drives:
    on = loudness(render(x, Blend=100, Drive=d))
    off = loudness(render(x, Blend=100, Drive=d, **{CAB: 1}))
    diffs.append(off - on)
    print(f"  Drive {d:3d} %: bypassed - voiced = {off - on:+.1f} dB")
check(
    abs(diffs[drives.index(50)]) < 1.5,
    f"Drive 50 %: bypassed is {diffs[drives.index(50)]:+.1f} dB from voiced (within 1.5 dB)",
)
ax.plot(drives, diffs, "o-")
ax.axhline(0, color="k", lw=0.5)
ax.set_title("Loudness, bypassed minus voiced (bass line, Blend 100 %)")
ax.set_xlabel("Drive (%)")
ax.set_ylabel("K-weighted difference (dB)")
ax.grid(True, alpha=0.3)

# The clean path doesn't pass through the voicing.
y0 = render(x, Blend=0, Drive=100)
y1 = render(x, Blend=0, Drive=100, **{CAB: 1})
dev = db(np.max(np.abs(y1 - y0)))
check(dev < -100, f"Blend 0: Cab Bypass changes the output by at most {dev:.0f} dBFS")

save_plot(fig, "cabsim")
write_csv("cabsim", ("input_dbfs", "cab_bypass", "freq_hz", "gain_db"), rows)
write_csv("cabsim_loudness", ("drive", "bypassed_minus_voiced_db"), zip(drives, diffs, strict=True))
finish()
