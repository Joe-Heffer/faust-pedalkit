# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Frequency response at several Distortion, Filter, Crossover and Low Blend settings.

Measured with Gaussian noise and an H1 cross-spectral estimate. At -70 dBFS the
diodes are not conducting, so the curve is the small-signal response. At
-20 dBFS the diodes clip and the curve is the best linear approximation.
"""

import numpy as np

from fxtest import SR, db, finish, plt, render, save_plot, transfer, write_csv

print("test_freqresp")
rng = np.random.default_rng(7)
noise = rng.normal(0, 1, 8 * SR)
dists = (0, 25, 50, 75, 100)
rows = []


def keep(panel, lvl, setting, f, H):
    """Record about 200 log-spaced points of a curve for the CSV."""
    idx = np.unique(
        np.geomspace(np.searchsorted(f, 20), np.searchsorted(f, 20000), 200).astype(int)
    )
    rows.extend((panel, lvl, setting, f[i], db(H[i])) for i in idx)


fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
for ax, lvl in zip(axes[0], (-70, -20), strict=True):
    x = noise * 10 ** (lvl / 20)
    for d in dists:
        y = render(x, Distortion=d, Filter=30)
        f, H = transfer(x, y)
        ax.semilogx(f[1:], db(H[1:]), label=f"Distortion {d}%")
        keep("distortion", lvl, f"Distortion {d}", f, H)
    ax.set_title(f"Input {lvl} dBFS RMS noise, Filter 30%, Crossover 120 Hz")
    ax.set_ylim(-20, 70)

x = noise * 10 ** (-70 / 20)
ax = axes[1, 0]
for fl in (0, 25, 50, 75, 100):
    y = render(x, Distortion=100, Filter=fl)
    f, H = transfer(x, y)
    ax.semilogx(f[1:], db(H[1:]), label=f"Filter {fl}%")
    keep("filter", -70, f"Filter {fl}", f, H)
ax.set_title("Filter at Distortion 100%, -70 dBFS noise")
ax.set_ylim(-20, 70)

ax = axes[1, 1]
for xo in (60, 120, 250, 400):
    y = render(x, Distortion=50, Filter=30, Crossover=xo, **{"Low Blend": 100})
    f, H = transfer(x, y)
    ax.semilogx(f[1:], db(H[1:]), label=f"Crossover {xo} Hz")
    keep("crossover", -70, f"Crossover {xo}", f, H)
ax.set_title("Crossover at Distortion 50%, Low Blend 100%, -70 dBFS noise")
ax.set_ylim(-20, 70)

for ax in axes.flat:
    ax.set_xlim(20, 20000)
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("gain (dB)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8)

save_plot(fig, "freqresp")
write_csv("freqresp", ("panel", "input_dbfs", "setting", "freq_hz", "gain_db"), rows)
finish()
