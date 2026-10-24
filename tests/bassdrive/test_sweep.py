# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Low E string sweep (41 Hz to 2 kHz), plus a low-end retention check.

The plots show the output spectrum over time (spectrogram) and the output
level against the instantaneous sweep frequency for several Gain settings.
"""

import numpy as np

from fxtest import (
    OUT,
    SR,
    check,
    db,
    finish,
    harmonics,
    log_sweep,
    plt,
    render,
    save_plot,
    sine,
    write_csv,
    write_wav,
)

print("test_sweep")
DUR = 8.0
x, finst = log_sweep(41.2, 2000, DUR, amp_db=-12)
gains = (0, 50, 100)
level_rows = []

fig, axes = plt.subplots(2, 3, figsize=(15, 8), constrained_layout=True)
for col, g in enumerate(gains):
    y = render(x, Gain=g, Balance=100)
    check(np.all(np.isfinite(y)), f"sweep, Gain {g}: output finite")
    write_wav(f"{OUT}/sweep_gain{g}.wav", y)
    ax = axes[0, col]
    ax.specgram(y, NFFT=4096, Fs=SR, noverlap=3072, cmap="magma", vmin=-140)
    ax.set_yscale("log")
    ax.set_ylim(30, 20000)
    ax.set_title(f"Driven only, Gain {g}%")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("frequency (Hz)")

    # Level against sweep frequency, 50 ms RMS windows.
    ax = axes[1, 0]
    w = int(0.05 * SR)
    n = len(y) // w
    rms = np.sqrt(np.mean(y[: n * w].reshape(n, w) ** 2, axis=1))
    fmid = finst[w // 2 :: w][:n]
    ax.semilogx(fmid, db(rms) + 3.01, label=f"Gain {g}%")
    level_rows.extend((g, fq, lv) for fq, lv in zip(fmid, db(rms) + 3.01, strict=True))

ax = axes[1, 0]
ax.set_title("Output level vs sweep frequency (Balance 100%)")
ax.set_xlabel("sweep frequency (Hz)")
ax.set_ylabel("level (dBFS peak-equivalent)")
ax.grid(True, which="both", alpha=0.3)
ax.legend()

# Low-end retention: the low E fundamental at Balance 50% should hold up as
# Gain rises, because the clean path is full-range.
fund = {}
ax = axes[1, 1]
for g in (0, 25, 50, 75, 100):
    y = render(sine(41, 3, -12), Gain=g, Balance=50)
    fund[g] = db(harmonics(y, 41, 1)[0])
ax.plot(list(fund), list(fund.values()), "o-")
ax.set_title("41 Hz fundamental at Balance 50%")
ax.set_xlabel("Gain (%)")
ax.set_ylabel("fundamental (dBFS)")
ax.grid(True, alpha=0.3)
spread = max(fund.values()) - min(fund.values())
check(spread < 6.0, f"low E fundamental spread over Gain 0-100% = {spread:.2f} dB (< 6 dB)")
print("  fundamental dBFS by Gain:", {k: round(v, 2) for k, v in fund.items()})

# Balance sweep at full Gain, same check from the other direction.
ax = axes[1, 2]
lvl = {}
for b in (0, 25, 50, 75, 100):
    y = render(sine(41, 3, -12), Gain=100, Balance=b)
    lvl[b] = db(harmonics(y, 41, 1)[0])
ax.plot(list(lvl), list(lvl.values()), "o-")
ax.set_title("41 Hz fundamental at Gain 100%")
ax.set_xlabel("Balance (%)")
ax.set_ylabel("fundamental (dBFS)")
ax.grid(True, alpha=0.3)
print("  fundamental dBFS by Balance:", {k: round(v, 2) for k, v in lvl.items()})

save_plot(fig, "sweep_lowE")
write_csv("sweep_level", ("gain", "freq_hz", "level_db"), level_rows)
write_csv(
    "lowE_fundamental",
    ("sweep", "setting", "fundamental_dbfs"),
    [("gain", k, v) for k, v in fund.items()] + [("balance", k, v) for k, v in lvl.items()],
)
finish()
