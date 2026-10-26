# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""The measurable targets in docs/bassgrit/design-notes.md, section 5."""

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
rng = np.random.default_rng(11)
noise = rng.normal(0, 1, 8 * SR)
small = noise * 10 ** (-70 / 20)  # diodes not conducting: small-signal response
OUT_TRIM_DB = db(1.2)  # outTrim in src/bassgrit.dsp
BL = "Low Blend"


def gain_at(f, H, f0):
    return float(db(H[np.argmin(np.abs(f - f0))]))


rows = []

# 1. With Distortion 0, Filter 0 and Low Blend 100 the two bands sum back to
#    the input: the response is flat (the all-pass sum of the crossover) apart
#    from outTrim, which also proves the clean band is time-aligned.
y = render(small, Distortion=0, Filter=0, **{BL: 100})
f, H = transfer(small, y)
band = (f > 30) & (f < 8000)
dev = np.abs(db(H[band]) - OUT_TRIM_DB)
check(
    np.max(dev) < 1.0,
    f"1. Distortion 0 is flat within {np.max(dev):.2f} dB of outTrim, 30 Hz-8 kHz (< 1)",
)
rows.append(("flat_deviation_db", np.max(dev)))

# 2. The fundamental of a low note stays in the clean band: 41 Hz gain at
#    Distortion 50 is within 3 dB of Distortion 0, while 1 kHz rises by > 25 dB.
y0 = render(small, Distortion=0, Filter=0, **{BL: 100})
y50 = render(small, Distortion=50, Filter=0, **{BL: 100})
f, H0 = transfer(small, y0)
_, H50 = transfer(small, y50)
low_shift = gain_at(f, H50, 41) - gain_at(f, H0, 41)
mid_shift = gain_at(f, H50, 1000) - gain_at(f, H0, 1000)
check(abs(low_shift) < 3, f"2. 41 Hz moves {low_shift:+.1f} dB from Distortion 0 to 50 (|x| < 3)")
check(mid_shift > 25, f"2. 1 kHz rises {mid_shift:+.1f} dB from Distortion 0 to 50 (> 25)")
rows += [("low_shift_db", low_shift), ("mid_shift_db", mid_shift)]


# 3. The split is what keeps a low note clean: 41 Hz at -12 dBFS, Distortion 50,
#    has at least 20 dB less harmonic distortion at Crossover 120 Hz than at 40 Hz.
def thd(xover):
    yy = render(sine(41, 3, -12), Distortion=50, Filter=30, Crossover=xover, **{BL: 100})
    hk = harmonics(yy, 41, 10)
    return float(db(np.sqrt(np.sum(hk[1:] ** 2)) / hk[0]))


t120, t40 = thd(120), thd(40)
check(
    t40 - t120 >= 20,
    f"3. 41 Hz THD {t120:.1f} dB at 120 Hz vs {t40:.1f} dB at 40 Hz (>= 20 dB better)",
)
rows += [("thd_41hz_crossover120_db", t120), ("thd_41hz_crossover40_db", t40)]

# 4. Small-signal gain at 1 kHz runs from about 0 dB at Distortion 0 to above
#    45 dB at Distortion 100 (Rf/RB = 178 is 45 dB; the 47 ohm leg adds more).
y100 = render(small, Distortion=100, Filter=0, **{BL: 100})
_, H100 = transfer(small, y100)
g0, g100 = gain_at(f, H0, 1000), gain_at(f, H100, 1000)
check(
    g0 < 3 and g100 > 45,
    f"4. 1 kHz gain {g0:.1f} dB at Distortion 0 to {g100:.1f} dB at 100 (< 3, > 45)",
)
rows += [("gain_1k_d0_db", g0), ("gain_1k_d100_db", g100)]

# 5. The gain-bandwidth pole: at Distortion 100 the response has fallen at least
#    6 dB from its 1 kHz value by 5 kHz, and at Distortion 50 by less.
d100 = gain_at(f, H100, 5000) - gain_at(f, H100, 1000)
d50 = gain_at(f, H50, 5000) - gain_at(f, H50, 1000)
check(
    d100 < -6 and d50 > d100 + 3,
    f"5. 5 kHz relative to 1 kHz: {d100:+.1f} dB at Distortion 100, "
    f"{d50:+.1f} dB at 50 (< -6 and 3 dB apart)",
)
rows += [("roll_5k_d100_db", d100), ("roll_5k_d50_db", d50)]

# 6. Filter: the response at Filter 100 over Filter 0 follows the analytic
#    one-pole ratio (Rs + pot into 4.7 nF) within 0.7 dB from 100 Hz to 5 kHz.
Rs, Cf = 1.5e3, 4.7e-9
yf0 = render(small, Distortion=0, Filter=0, **{BL: 0})
yf1 = render(small, Distortion=0, Filter=100, **{BL: 0})
_, HF0 = transfer(small, yf0)
_, HF1 = transfer(small, yf1)
fb = f[(f > 100) & (f < 5000)]
fc0, fc1 = 1 / (2 * np.pi * Rs * Cf), 1 / (2 * np.pi * (Rs + 100e3) * Cf)
expect = np.sqrt((1 + (fb / fc0) ** 2) / (1 + (fb / fc1) ** 2))
meas = np.abs(HF1[(f > 100) & (f < 5000)] / HF0[(f > 100) & (f < 5000)])
err = float(np.max(np.abs(db(meas / expect))))
check(
    err < 0.7,
    f"6. Filter 100/Filter 0 ratio within {err:.2f} dB of analytic, corner {fc1:.0f} Hz (< 0.7)",
)
rows.append(("filter_ratio_error_db", err))

# 7. Low Blend restores the low band at playing level: at -20 dBFS and
#    Distortion 50, Low Blend 100 lifts 30-60 Hz by at least 6 dB over 0. At
#    Distortion 100 the lift is smaller (the driven path still carries some
#    30-60 Hz energy, see the design notes) and is reported only.
xl = noise * 10 ** (-20 / 20)
for d in (50, 100):
    _, L0 = transfer(xl, render(xl, Distortion=d, Filter=30, **{BL: 0}))
    fl, L1 = transfer(xl, render(xl, Distortion=d, Filter=30, **{BL: 100}))
    low = (fl > 30) & (fl < 60)
    rise = float(np.mean(db(L1[low])) - np.mean(db(L0[low])))
    if d == 50:
        check(
            rise >= 6, f"7. Low Blend 100 lifts 30-60 Hz by {rise:+.1f} dB at Distortion 50 (>= 6)"
        )
    else:
        print(f"  7. (reported) lift at Distortion 100: {rise:+.1f} dB")
    rows.append((f"blend_lift_d{d}_db", rise))

# 8. At Distortion 25 the output follows the input level up to the diodes and
#    then compresses: each 10 dB step rises, and the last rises by less than 6 dB.
levels = (-50, -40, -30, -20)
amps = []
for lv in levels:
    hk = harmonics(render(sine(1000, 2, lv), Distortion=25, Filter=0), 1000, 1)
    amps.append(float(db(hk[0])))
steps = [b - a for a, b in zip(amps, amps[1:], strict=False)]
check(
    all(s > 0 for s in steps) and steps[-1] < 6,
    f"8. 10 dB input steps give {[round(s, 1) for s in steps]} dB at 1 kHz (all > 0, last < 6)",
)
rows.append(("compression_last_step_db", steps[-1]))

fig, ax = plt.subplots(figsize=(7, 4.5), constrained_layout=True)
ax.semilogx(f[1:], db(H0[1:]), label="Distortion 0")
ax.semilogx(f[1:], db(H50[1:]), label="Distortion 50")
ax.semilogx(f[1:], db(H100[1:]), label="Distortion 100")
ax.set_xlim(20, 20000)
ax.set_ylim(-10, 70)
ax.set_xlabel("frequency (Hz)")
ax.set_ylabel("gain (dB)")
ax.set_title("Small-signal response, Filter 0%, Low Blend 100%")
ax.grid(True, which="both", alpha=0.3)
ax.legend()
save_plot(fig, "targets")
write_csv("targets", ("quantity", "value"), rows)
finish()
