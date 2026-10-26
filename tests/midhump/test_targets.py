# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""The measurable targets from docs/midhump/design-notes.md.

1. The small-signal response matches the analytic circuit model.
2. The response has a mid hump: its peak is at 500-1500 Hz at Drive 100, and
   100 Hz sits well below it.
3. Output keeps rising with input level after the diodes conduct (the clean
   term is never clipped away).
4. Drive moves the gain by the reported 21 to 41 dB at 2 kHz.
"""

import numpy as np

from fxtest import (
    SR,
    check,
    db,
    finish,
    harmonics,
    plt,
    render,
    save_plot,
    sine,
    transfer,
    write_csv,
)

print("test_targets")

# Constants repeated from src/midhump.dsp, so a change there fails this test.
R4, C3, R6, RPOT, C4 = 4.7e3, 47e-9, 51e3, 500e3, 51e-12
FC_IN = 1 / (2 * np.pi * 510e3 * 20e-9)
FC_PASSIVE = 1 / (2 * np.pi * 1e3 * 220e-9)
FC_SHELF = 1 / (2 * np.pi * 220 * 220e-9)


def analytic(f, drive, tone):
    """Complex small-signal response of the model, from the circuit equations."""
    s = 1j * f
    rf = R6 + RPOT * (10 ** (2 * drive) - 1) / 99
    hp = s / (s + 1 / (2 * np.pi * R4 * C3))
    lp = 1 / (1 + s * 2 * np.pi * rf * C4)
    clip_stage = 1 + (rf / R4) * hp * lp
    fz = FC_SHELF * (FC_PASSIVE / FC_SHELF) ** tone
    shelf = (1 + s / fz) / (1 + s / FC_SHELF)
    passive = 1 / (1 + s / FC_PASSIVE)
    coupling = s / (s + FC_IN)
    return coupling * clip_stage * passive * shelf


rng = np.random.default_rng(3)
noise = rng.normal(0, 1, 8 * SR) * 10 ** (-70 / 20)
rows = []
fig, axes = plt.subplots(1, 3, figsize=(16, 5), constrained_layout=True)

# 1. Analytic match, 50 Hz to 4 kHz.
ax = axes[0]
for d in (0, 50, 100):
    y = render(noise, Drive=d, Tone=50)
    f, H = transfer(noise, y)
    band = (f >= 50) & (f <= 4000)
    ref = analytic(f[band], d / 100, 0.5)
    err = db(H[band]) - db(ref)
    worst = np.max(np.abs(err))
    check(worst < 1.5, f"Drive {d}: model within {worst:.2f} dB of the analytic response (< 1.5)")
    ax.semilogx(f[band], db(H[band]), label=f"measured, Drive {d}%")
    ax.semilogx(f[band], db(ref), "k:", lw=0.8)
    rows.extend(("analytic", d, fq, e) for fq, e in zip(f[band][::8], err[::8], strict=True))
ax.set_title("Measured against analytic (dotted)")
ax.set_xlabel("frequency (Hz)")
ax.set_ylabel("gain (dB)")
ax.legend(fontsize=8)
ax.grid(True, which="both", alpha=0.3)

# 2. Mid hump at Drive 100, Tone 50.
y = render(noise, Drive=100, Tone=50)
f, H = transfer(noise, y)
band = (f >= 40) & (f <= 8000)
peak_f = f[band][np.argmax(db(H[band]))]
at100 = db(H[np.argmin(np.abs(f - 100))])
peak = np.max(db(H[band]))
check(500 <= peak_f <= 1500, f"response peak at {peak_f:.0f} Hz (500-1500 Hz)")
check(peak - at100 >= 8, f"100 Hz is {peak - at100:.1f} dB below the peak (>= 8 dB)")

# 3. Fundamental against input level at 1 kHz, Drive 100.
ax = axes[1]
levels = np.arange(-60, 1, 6)
out = [db(harmonics(render(sine(1000, 2, lv), Drive=100, Tone=50), 1000, 1)[0]) for lv in levels]
ax.plot(levels, out, "o-")
ax.set_title("1 kHz fundamental against input level, Drive 100%")
ax.set_xlabel("input (dBFS)")
ax.set_ylabel("output fundamental (dBFS)")
ax.grid(True, alpha=0.3)
rows.extend(("level", lv, 0, o) for lv, o in zip(levels, out, strict=True))
check(
    all(b > a for a, b in zip(out[-4:], out[-3:], strict=False)),
    "output fundamental still rises with input once the diodes conduct",
)

# 4. Gain at 2 kHz against Drive, from the reported 21 to 41 dB range of the
# clipping stage alone (Tone 0 leaves only the 723 Hz low-pass, which is
# removed by comparing against the analytic passive section).
ax = axes[2]
drives = np.arange(0, 101, 10)
g2k = []
for d in drives:
    yy = render(noise, Drive=int(d), Tone=0)
    ff, HH = transfer(noise, yy)
    i = np.argmin(np.abs(ff - 2000))
    g2k.append(db(HH[i]) - db(1 / (1 + 1j * ff[i] / FC_PASSIVE)))
ax.plot(drives, g2k, "o-")
ax.set_title("Gain at 2 kHz (passive low-pass removed), Tone 0%")
ax.set_xlabel("Drive (%)")
ax.set_ylabel("gain (dB)")
ax.grid(True, alpha=0.3)
check(18 <= g2k[0] <= 24, f"Drive 0 gain at 2 kHz {g2k[0]:.1f} dB (about 21)")
check(36 <= g2k[-1] <= 42, f"Drive 100 gain at 2 kHz {g2k[-1]:.1f} dB (about 41)")
rows.extend(("gain2k", d, 2000, g) for d, g in zip(drives, g2k, strict=True))

save_plot(fig, "targets")
write_csv("targets", ("panel", "setting", "x", "value"), rows)
finish()
