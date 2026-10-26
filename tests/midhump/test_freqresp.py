# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Frequency response at several Drive and Tone settings, and the Blend path.

Measured with Gaussian noise and an H1 cross-spectral estimate. At -70 dBFS the
diodes are not conducting, so the curve is the small-signal response. At
-20 dBFS the diodes clip and the curve is the best linear approximation.
"""

import numpy as np

from fxtest import SR, check, db, finish, plt, render, save_plot, transfer, write_csv

print("test_freqresp")
rng = np.random.default_rng(7)
noise = rng.normal(0, 1, 8 * SR)
drives = (0, 25, 50, 75, 100)
rows = []


def keep(panel, lvl, drive, tone, blend, f, H):
    """Record about 200 log-spaced points of a curve for the CSV."""
    idx = np.unique(
        np.geomspace(np.searchsorted(f, 20), np.searchsorted(f, 20000), 200).astype(int)
    )
    rows.extend((panel, lvl, drive, tone, blend, f[i], db(H[i])) for i in idx)


fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
for ax, lvl in zip(axes[0], (-70, -20), strict=True):
    x = noise * 10 ** (lvl / 20)
    for d in drives:
        y = render(x, Drive=d, Tone=50)
        f, H = transfer(x, y)
        ax.semilogx(f[1:], db(H[1:]), label=f"Drive {d}%")
        keep("drive", lvl, d, 50, 0, f, H)
    ax.set_title(f"Input {lvl} dBFS RMS noise, Tone 50%")
    ax.set_ylim(-10, 50)

x = noise * 10 ** (-70 / 20)
ax = axes[1, 0]
for tn in (0, 25, 50, 75, 100):
    y = render(x, Drive=100, Tone=tn)
    f, H = transfer(x, y)
    ax.semilogx(f[1:], db(H[1:]), label=f"Tone {tn}%")
    keep("tone", -70, 100, tn, 0, f, H)
ax.set_title("Tone at Drive 100%, -70 dBFS noise")
ax.set_ylim(-10, 50)

ax = axes[1, 1]
for bl in (0, 50, 100):
    y = render(x, Drive=50, Tone=50, Blend=bl)
    f, H = transfer(x, y)
    ax.semilogx(f[1:], db(H[1:]), label=f"Blend {bl}%")
    keep("blend", -70, 50, 50, bl, f, H)
    if bl == 100:
        band = (f > 30) & (f < 60)
        y0 = render(x, Drive=50, Tone=50, Blend=0)
        _, H0 = transfer(x, y0)
        rise = np.mean(db(H[band])) - np.mean(db(H0[band]))
        check(2.5 < rise < 4.5, f"Blend 100% lifts 30-60 Hz by {rise:+.2f} dB (expect about +3.5)")
ax.set_title("Blend at Drive 50%, Tone 50%, -70 dBFS noise")
ax.set_ylim(-10, 50)

for ax in axes.flat:
    ax.set_xlim(20, 20000)
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("gain (dB)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8)

save_plot(fig, "freqresp")
write_csv(
    "freqresp",
    ("panel", "input_dbfs", "drive", "tone", "blend", "freq_hz", "gain_db"),
    rows,
)
finish()
