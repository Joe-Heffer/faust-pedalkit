"""Frequency response of the preamp path at several Drive and Presence
settings, and of the three-band EQ with both shift positions.

Measured with Gaussian noise and an H1 cross-spectral estimate. At -70 dBFS
the clippers are idle, so those panels are the small-signal response. At
-20 dBFS the clippers are active and the curve is the best linear
approximation.
"""

import numpy as np

from fxtest import OUT, SR, check, db, finish, plt, render, transfer

print("test_freqresp")
rng = np.random.default_rng(7)
noise = rng.normal(0, 1, 8 * SR)
SHIFT = ("Bass Shift", "Mid Shift")


def resp(lvl, **params):
    x = noise * 10 ** (lvl / 20)
    return transfer(x, render(x, **params))


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
        f, H = resp(lvl, Drive=d, Blend=100)
        ax.semilogx(f[1:], db(H[1:]), label=f"Drive {d}%")
    panel(ax, f"Blend 100%, Presence 50%, {lvl} dBFS noise", (-40, 40 if lvl == -70 else 20))

# Presence at Drive 0: boost only.
ax = axes[0, 1]
curves = {}
for p in (0, 25, 50, 75, 100):
    f, H = resp(-70, Drive=0, Presence=p, Blend=100)
    curves[p] = db(H)
    ax.semilogx(f[1:], db(H[1:]), label=f"Presence {p}%")
panel(ax, "Presence (Drive 0%, Blend 100%, -70 dBFS)", (-40, 20))
# Below ~500 Hz the stage is near unity at every setting; the small dip there
# comes from the phase interaction with the clean lows that pass below 34 Hz.
diff = curves[100] - curves[0]
band = (f > 150) & (f < 8000)
check(
    np.all(diff[band] > -1.5),
    f"Presence only boosts: 100 % vs 0 % >= {np.min(diff[band]):+.1f} dB from 150 Hz to 8 kHz",
)
# Measured below 3 kHz: higher up, the preamp path at Presence 0 is down at
# the level of the clean signal that leaks through C16 and the Blend pot, and
# the two partly cancel.
band = (f > 1000) & (f < 3000)
check(
    np.max(diff[band]) > 15,
    f"Presence range in 1-3 kHz: {np.max(diff[band]):.1f} dB "
    "(> 15 dB; analysis gives 21.7 dB at 3 kHz)",
)

# Fixed speaker voicing: the preamp path rolls off steeply above ~5 kHz.
f, H = resp(-70, Drive=50, Blend=100)
hi = at(f, H, 12000) - np.max(db(H[(f > 100) & (f < 5000)]))
check(hi < -20, f"preamp path at 12 kHz is {hi:.1f} dB below its peak (< -20 dB)")

# Clean path with a flat EQ is flat.
f, H = resp(-20, Blend=0)
band = (f > 30) & (f < 15000)
dev = np.max(np.abs(db(H[band])))
check(dev < 0.5, f"Blend 0, flat EQ: within +/-{dev:.2f} dB from 30 Hz to 15 kHz")

# Bass and Treble shelves, both Bass Shift positions.
ax = axes[0, 2]
for shift, fx in ((0, 80), (1, 40)):
    for g in (-12, 12):
        f, H = resp(-20, Blend=0, Bass=g, **{SHIFT[0]: shift})
        ax.semilogx(f[1:], db(H[1:]), label=f"Bass {g:+d}, shift {shift}")
        if g == 12:
            # 3rd-order shelf: about 3 dB short of full boost at fx.
            mid, low, above = at(f, H, fx), at(f, H, fx / 3), at(f, H, 4 * fx)
            check(
                7 < mid < 10.5 and low > 10 and above < 2,
                f"Bass +12, shift {shift}: {mid:+.1f} dB at {fx} Hz, {low:+.1f} dB at "
                f"{fx / 3:.0f} Hz, {above:+.1f} dB at {4 * fx} Hz",
            )
for g in (-12, 12):
    f, H = resp(-20, Blend=0, Treble=g)
    ax.semilogx(f[1:], db(H[1:]), "--", label=f"Treble {g:+d}")
    if g == 12:
        check(
            7 < at(f, H, 2800) < 10.5 and at(f, H, 12000) > 11 and at(f, H, 700) < 2,
            f"Treble +12: {at(f, H, 700):+.1f} dB at 700 Hz, {at(f, H, 2800):+.1f} dB at 2.8 kHz, "
            f"{at(f, H, 12000):+.1f} dB at 12 kHz",
        )
panel(ax, "Bass and Treble (Blend 0%)", (-15, 15))

# Mid band, both Mid Shift positions.
ax = axes[1, 1]
for shift, fx in ((0, 500), (1, 1000)):
    for g in (-12, 12):
        f, H = resp(-20, Blend=0, Mid=g, **{SHIFT[1]: shift})
        ax.semilogx(f[1:], db(H[1:]), label=f"Mid {g:+d}, shift {shift}")
        band = (f > 100) & (f < 5000)
        k = np.argmax(np.sign(g) * db(H[band]))
        fpk, gpk = f[band][k], db(H[band])[k]
        check(
            abs(np.log2(fpk / fx)) < 0.15 and abs(abs(gpk) - 12) < 0.7,
            f"Mid {g:+d}, shift {shift}: extreme {gpk:+.1f} dB at {fpk:.0f} Hz (want {fx} Hz)",
        )
panel(ax, "Mid (Blend 0%)", (-15, 15))

# Blend at full Drive: the C16 coupling keeps the clean lows below ~34 Hz.
ax = axes[1, 2]
for b in (0, 25, 50, 75, 100):
    f, H = resp(-20, Drive=100, Blend=b)
    ax.semilogx(f[1:], db(H[1:]), label=f"Blend {b}%")
panel(ax, "Blend at Drive 100% (-20 dBFS)", (-30, 30))

fig.savefig(f"{OUT}/freqresp.png", dpi=110)
print(f"  wrote {OUT}/freqresp.png")
finish()
