# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Frequency response at rest and with Feedback (design-notes target 1).

With Follow 0 and Sweep 0 the wet delay sits at the zero point, so wet and
dry are the same signal. With Feedback 0 the output is then the crossover's
all-pass at any Depth. With Feedback up, the loop round the wet delay leaves
a static comb.
"""

import numpy as np

from fxtest import SR, check, db, finish, plt, render, save_plot, transfer, write_csv

print("test_freqresp")
rng = np.random.default_rng(7)
x = rng.normal(0, 10 ** (-30 / 20), 8 * SR)
ZERO_SAMPLES = 96  # repeated from src/basstide.dsp
rows = []


def keep(panel, depth, feedback, f, H):
    """Record about 200 log-spaced points of a curve for the CSV."""
    idx = np.unique(
        np.geomspace(np.searchsorted(f, 20), np.searchsorted(f, 20000), 200).astype(int)
    )
    rows.extend((panel, depth, feedback, f[i], db(H[i])) for i in idx)


fig, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
ax = axes[0]
for depth in (0, 50, 100):
    y = render(x, Follow=0, Sweep=0, Feedback=0, Depth=depth)
    f, H = transfer(x, y)
    # The 5 Hz DC blocker alone takes 0.26 dB off at 20 Hz, so the flatness
    # band starts at 40 Hz (0.07 dB from the blocker). CI measured 0.103 dB over 40 Hz to
    # 20 kHz, so the limit is 0.15 dB; the other 0.04 dB is not yet attributed.
    band = (f > 40) & (f < 20000)
    dev = np.max(np.abs(db(H[band])))
    check(dev < 0.15, f"at rest, Depth {depth}: flat within {dev:.3f} dB (< 0.15)")
    ax.semilogx(f[1:], db(H[1:]), label=f"Depth {depth}%")
    keep("rest", depth, 0, f, H)
ax.set_title("At rest (Follow 0, Sweep 0, Feedback 0)")
ax.set_ylim(-30, 25)

ax = axes[1]
for feedback in (-90, -50, 0, 50, 90):
    y = render(x, Follow=0, Sweep=0, Feedback=feedback, Depth=100)
    f, H = transfer(x, y)
    ax.semilogx(f[1:], db(H[1:]), lw=0.8, label=f"Feedback {feedback}%")
    keep("feedback", 100, feedback, f, H)
spacing = SR / (ZERO_SAMPLES + 1)
ax.set_title(f"Feedback at rest, Depth 100% (comb spacing {spacing:.0f} Hz)")
ax.set_ylim(-30, 25)

for ax in axes:
    ax.set_xlim(20, 20000)
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("gain (dB)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8)

save_plot(fig, "freqresp")
write_csv("freqresp", ("panel", "depth", "feedback", "freq_hz", "gain_db"), rows)
finish()
