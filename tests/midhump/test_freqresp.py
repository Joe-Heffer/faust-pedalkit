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
# Repeated from src/midhump.dsp and src/lib/pedalkit.lib.
FC_IN = 1 / (2 * np.pi * 510e3 * 20e-9)
OS4_LATENCY = 32
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
    if bl == 0:
        H0 = H
    if bl == 100:
        # The clean path is linear, so Blend 100 minus Blend 0 should be
        # exactly cleanTrim times the input high-pass, delayed by the same
        # os4Latency as the driven path. Any misalignment would show here as
        # a phase ramp (and as comb filtering in the blend).
        band = (f > 100) & (f < 10000)
        fb = f[band]
        expect = 0.5 * (1j * fb / (1j * fb + FC_IN)) * np.exp(-2j * np.pi * fb * OS4_LATENCY / SR)
        ratio = (H[band] - H0[band]) / expect
        mag_err = np.max(np.abs(db(ratio)))
        ph_err = np.degrees(np.max(np.abs(np.angle(ratio))))
        check(mag_err < 0.3, f"Blend path is 0.5 x input within {mag_err:.2f} dB (< 0.3)")
        check(ph_err < 2, f"Blend path is time-aligned within {ph_err:.2f} deg (< 2)")

# Low-end lift at playing level. At -20 dBFS the feedback branch clips, so the
# clean half-amplitude copy adds to bass that the driven path holds near unity.
# (At -70 dBFS the unclipped branch is large even at 45 Hz and the lift falls
# from 2.6 dB at Drive 0 to 0.1 dB at Drive 100.)
xl = noise * 10 ** (-20 / 20)
for d in (0, 50, 100):
    _, L0 = transfer(xl, render(xl, Drive=d, Tone=50, Blend=0))
    fl, L1 = transfer(xl, render(xl, Drive=d, Tone=50, Blend=100))
    low = (fl > 30) & (fl < 60)
    rise = np.mean(db(L1[low])) - np.mean(db(L0[low]))
    check(
        2 < rise < 4.5,
        f"Drive {d}, -20 dBFS: Blend 100% lifts 30-60 Hz by {rise:+.2f} dB (2 to 4.5)",
    )
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
