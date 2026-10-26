# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Low E string sweep (41 Hz to 2 kHz) through the driven path.

The plots show the output spectrum over time (spectrogram) and the output
level against the instantaneous sweep frequency for several Distortion settings.
"""

import numpy as np

from fxtest import (
    OUT,
    SR,
    check,
    db,
    finish,
    log_sweep,
    plt,
    render,
    save_plot,
    write_csv,
    write_wav,
)

print("test_sweep")
DUR = 8.0
x, finst = log_sweep(41.2, 2000, DUR, amp_db=-12)
distortions = (0, 50, 100)
level_rows = []

fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
ax_level = axes[1, 1]
for ax, d in zip(axes.flat[:3], distortions, strict=True):
    y = render(x, Distortion=d, Filter=30)
    check(np.all(np.isfinite(y)), f"sweep, Distortion {d}: output finite")
    write_wav(f"{OUT}/sweep_distortion{d}.wav", y)
    ax.specgram(y, NFFT=4096, Fs=SR, noverlap=3072, cmap="magma", vmin=-140)
    ax.set_yscale("log")
    ax.set_ylim(30, 20000)
    ax.set_title(f"Distortion {d}%")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("frequency (Hz)")

    w = int(0.05 * SR)
    n = len(y) // w
    rms = np.sqrt(np.mean(y[: n * w].reshape(n, w) ** 2, axis=1))
    fmid = finst[w // 2 :: w][:n]
    ax_level.semilogx(fmid, db(rms) + 3.01, label=f"Distortion {d}%")
    level_rows.extend((d, fq, lv) for fq, lv in zip(fmid, db(rms) + 3.01, strict=True))

ax_level.set_title("Output level vs sweep frequency")
ax_level.set_xlabel("sweep frequency (Hz)")
ax_level.set_ylabel("level (dBFS peak-equivalent)")
ax_level.grid(True, which="both", alpha=0.3)
ax_level.legend()

save_plot(fig, "sweep")
write_csv("sweep_level", ("distortion", "freq_hz", "level_db"), level_rows)
finish()
