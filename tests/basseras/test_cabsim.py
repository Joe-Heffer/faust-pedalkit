# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Cab Bypass: the bypassed preamp path is loudness-matched to the voiced one
at the defaults, and the clean path is unaffected. The shape of the speaker
sim itself is checked in test_freqresp.py."""

import numpy as np

from fxtest import SR, check, db, finish, loudness, plt, render, save_plot, write_csv

print("test_cabsim")
CAB = "Cab Bypass"


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


x = bass_line()
drives = (0, 30, 60, 100)
rows = []
for c in (0, 50, 100):
    for d in drives:
        on = loudness(render(x, Drive=d, Character=c))
        off = loudness(render(x, Drive=d, Character=c, **{CAB: 1}))
        rows.append((c, d, off - on))
        print(f"  Character {c:3d}% Drive {d:3d}%: bypassed - voiced = {off - on:+.1f} dB")
diff = dict(((c, d), v) for c, d, v in rows)[(50, 30)]
check(abs(diff) < 1.5, f"defaults: bypassed is {diff:+.1f} dB from voiced (within 1.5 dB)")

fig, ax = plt.subplots(figsize=(7, 5), constrained_layout=True)
for c in (0, 50, 100):
    ax.plot(drives, [v for cc, _, v in rows if cc == c], "o-", label=f"Character {c}%")
ax.axhline(0, color="k", lw=0.5)
ax.set_title("Loudness, bypassed minus voiced (bass line, Blend 100 %)")
ax.set_xlabel("Drive (%)")
ax.set_ylabel("K-weighted difference (dB)")
ax.grid(True, alpha=0.3)
ax.legend()

y0 = render(x, Blend=0, Drive=100)
y1 = render(x, Blend=0, Drive=100, **{CAB: 1})
dev = db(np.max(np.abs(y1 - y0)))
check(dev < -100, f"Blend 0: Cab Bypass changes the output by at most {dev:.0f} dBFS")

save_plot(fig, "cabsim")
write_csv("cabsim", ("character", "drive", "bypassed_minus_voiced_db"), rows)
finish()
