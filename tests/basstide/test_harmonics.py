# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""BassTide is linear in the audio: a steady sine at rest comes out with no
harmonics (design-notes target 8). It has no waveshaper and does not
oversample, so there is no aliasing comparison against RENDER_1X."""

import numpy as np

from fxtest import check, db, finish, harmonics, plt, render, save_plot, sine, write_csv

print("test_harmonics")
rows = []
fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
width = 0.25
for i, f0 in enumerate((41, 110, 220)):
    # Defaults: Follow 100, so after the onset at the start of the tone the
    # sweep glides back to the zero point and the last second is at rest.
    y = render(sine(f0, 4, -12))
    hk = harmonics(y, f0, 10)
    rel = db(hk / hk[0])
    rows.extend((f0, k, rel[k - 1]) for k in range(1, 11))
    worst = np.max(rel[1:])
    check(worst < -80, f"{f0} Hz at the defaults: highest harmonic {worst:.1f} dBc (< -80)")
    ax.bar(np.arange(1, 11) + (i - 1) * width, rel + 160, width, bottom=-160, label=f"{f0} Hz")
ax.set_title("Harmonics of a -12 dBFS sine at the defaults (sweep at rest)")
ax.set_xlabel("harmonic number")
ax.set_ylabel("level relative to fundamental (dB)")
ax.set_xticks(range(1, 11))
ax.set_ylim(-160, 5)
ax.grid(True, axis="y", alpha=0.3)
ax.legend()
save_plot(fig, "harmonics")
write_csv("harmonics", ("f0_hz", "harmonic", "level_dbc"), rows)
finish()
