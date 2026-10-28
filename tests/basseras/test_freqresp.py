# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Frequency response of the preamp path against Drive, of the speaker sim,
of the three-band EQ and of the Blend.

Measured with Gaussian noise and an H1 cross-spectral estimate. At -70 dBFS
the clippers are idle, so those panels are the small-signal response. At
-20 dBFS the clippers are active and the curve is the best linear
approximation.
"""

import numpy as np

from fxtest import SR, check, db, finish, plt, render, save_plot, transfer, write_csv

print("test_freqresp")
rng = np.random.default_rng(7)
noise = rng.normal(0, 1, 8 * SR)
CAB = "Cab Bypass"
DEFAULTS = {
    "Blend": 100,
    "Drive": 30,
    "Character": 50,
    "Low": 0,
    "Mid": 0,
    "High": 0,
    "Bite": 100,
    CAB: 0,
}
rows = []


def resp(lvl, panel=None, **params):
    """Transfer function at input level lvl. With a panel name, also keep
    about 200 log-spaced points from 20 Hz to 20 kHz for the CSV."""
    x = noise * 10 ** (lvl / 20)
    f, H = transfer(x, render(x, **params))
    if panel:
        p = {**DEFAULTS, **params}
        idx = np.unique(
            np.geomspace(np.searchsorted(f, 20), np.searchsorted(f, 20000), 200).astype(int)
        )
        rows.extend((panel, lvl, *p.values(), f[i], db(H[i])) for i in idx)
    return f, H


def at(f, H, hz):
    return db(np.abs(H[np.argmin(np.abs(f - hz))]))


def panel(ax, title, ylim):
    ax.set_title(title)
    ax.set_xlim(20, 20000)
    ax.set_ylim(*ylim)
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("gain (dB)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8)


fig, axes = plt.subplots(2, 3, figsize=(17, 9), constrained_layout=True)

# Preamp path only (Blend 100) against Drive, small signal and driven.
for ax, lvl in ((axes[0, 0], -70), (axes[1, 0], -20)):
    for d in (0, 25, 50, 75, 100):
        f, H = resp(lvl, "drive", Drive=d)
        ax.semilogx(f[1:], db(H[1:]), label=f"Drive {d}%")
    panel(ax, f"Blend 100%, Character 50%, {lvl} dBFS noise", (-40, 40 if lvl == -70 else 20))

# Speaker sim: voiced over bypassed isolates it (the rest of the path is the
# same). Drive 0 and Bite 0 keep the clippers and the presence peak out.
ax = axes[0, 1]
f, Hv = resp(-70, "cab", Drive=0, Bite=0)
_, Hb = resp(-70, "cab", Drive=0, Bite=0, **{CAB: 1})
ratio = db(Hv) - db(Hb)
ratio -= ratio[np.argmin(np.abs(f - 1000))]
ax.semilogx(f[1:], db(Hv[1:]), label="voiced")
ax.semilogx(f[1:], db(Hb[1:]), label="Cab Bypass")
ax.semilogx(f[1:], ratio[1:], "k--", label="speaker sim alone (re 1 kHz)")
panel(ax, "Speaker sim (Drive 0%, Bite 0%, -70 dBFS)", (-40, 15))
f3 = f[np.argmax((f > 1000) & (ratio < -3))]
check(3500 <= f3 <= 5500, f"speaker sim: -3 dB at {f3:.0f} Hz (3.5 to 5.5 kHz)")
d10 = at(f, 10 ** (ratio / 20), 10000)
check(d10 <= -20, f"speaker sim: {d10:.1f} dB at 10 kHz relative to 1 kHz (<= -20 dB)")
band = (f > 80) & (f < 3000)
ripple = np.max(ratio[band]) - np.min(ratio[(f > 80) & (f < 1000)])
check(
    np.max(ratio[band]) < 1 and ripple < 1.5,
    f"speaker sim: smooth from 80 Hz to 3 kHz (peak {np.max(ratio[band]):+.2f} dB, "
    f"spread {ripple:.2f} dB up to 1 kHz)",
)

# Clean path with a flat EQ is flat.
f, H = resp(-20, Blend=0)
band = (f > 30) & (f < 15000)
dev = np.max(np.abs(db(H[band])))
check(dev < 0.5, f"Blend 0, flat EQ: within +/-{dev:.2f} dB from 30 Hz to 15 kHz")

# Low and High shelves (documented: +/-12 dB at 125 Hz and 3.2 kHz). The
# 2nd-order shelves (pk.lowShelf2, pk.highShelf2) give half the gain at the
# corner, nearly all of it a factor of 3 beyond, and cut mirrors boost.
ax = axes[0, 2]
for g in (-12, 12):
    f, H = resp(-20, "low_high", Blend=0, Low=g)
    ax.semilogx(f[1:], db(H[1:]), label=f"Low {g:+d}")
    s = np.sign(g)
    corner, below, above = s * at(f, H, 125), s * at(f, H, 40), s * at(f, H, 250)
    check(
        5 < corner < 7 and below > 11 and above < 1,
        f"Low {g:+d}: {s * corner:+.1f} dB at 125 Hz, {s * below:+.1f} dB at 40 Hz, "
        f"{s * above:+.1f} dB at 250 Hz",
    )
for g in (-12, 12):
    f, H = resp(-20, "low_high", Blend=0, High=g)
    ax.semilogx(f[1:], db(H[1:]), "--", label=f"High {g:+d}")
    s = np.sign(g)
    corner, above, below = s * at(f, H, 3200), s * at(f, H, 12000), s * at(f, H, 1600)
    check(
        5 < corner < 7 and above > 11 and below < 1,
        f"High {g:+d}: {s * below:+.1f} dB at 1.6 kHz, {s * corner:+.1f} dB at 3.2 kHz, "
        f"{s * above:+.1f} dB at 12 kHz",
    )
panel(ax, "Low and High (Blend 0%)", (-15, 15))

# Mid band (documented: +/-12 dB at 1 kHz).
ax = axes[1, 1]
for g in (-12, 12):
    f, H = resp(-20, "mid", Blend=0, Mid=g)
    ax.semilogx(f[1:], db(H[1:]), label=f"Mid {g:+d}")
    band = (f > 100) & (f < 8000)
    k = np.argmax(np.sign(g) * db(H[band]))
    fpk, gpk = f[band][k], db(H[band])[k]
    check(
        abs(np.log2(fpk / 1000)) < 0.15 and abs(abs(gpk) - 12) < 0.7,
        f"Mid {g:+d}: extreme {gpk:+.1f} dB at {fpk:.0f} Hz (want 1 kHz)",
    )
panel(ax, "Mid (Blend 0%)", (-15, 15))

# Blend at full Drive.
ax = axes[1, 2]
for b in (0, 25, 50, 75, 100):
    f, H = resp(-20, "blend", Drive=100, Blend=b)
    ax.semilogx(f[1:], db(H[1:]), label=f"Blend {b}%")
panel(ax, "Blend at Drive 100% (-20 dBFS)", (-30, 30))

save_plot(fig, "freqresp")
write_csv(
    "freqresp",
    ("panel", "input_dbfs", *(k.lower().replace(" ", "_") for k in DEFAULTS), "freq_hz", "gain_db"),
    rows,
)
finish()
