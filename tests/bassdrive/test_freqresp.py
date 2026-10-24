"""Frequency response at several Gain settings, and of the EQ on its own.

Measured with Gaussian noise and an H1 cross-spectral estimate. At -70 dBFS
the driven path is effectively linear, so that panel is the small-signal
response. At -20 dBFS the clipper is active and the curve is the best linear
approximation, which is roughly what the ear hears as the tonal balance.
"""

import numpy as np

from fxtest import OUT, SR, check, db, finish, plt, render, transfer

print("test_freqresp")
rng = np.random.default_rng(7)
noise = rng.normal(0, 1, 8 * SR)
gains = (0, 25, 50, 75, 100)

fig, axes = plt.subplots(2, 3, figsize=(16, 9), constrained_layout=True)
panels = [(-70, 100), (-70, 50), (-20, 100), (-20, 50)]
for ax, (lvl, bal) in zip(axes.flat[[0, 1, 3, 4]], panels, strict=True):
    x = noise * 10 ** (lvl / 20)
    for g in gains:
        y = render(x, Gain=g, Balance=bal)
        f, H = transfer(x, y)
        ax.semilogx(f[1:], db(H[1:]), label=f"Gain {g}%")
    ax.set_title(f"Input {lvl} dBFS RMS noise, Balance {bal}%")
    ax.set_xlim(20, 20000)
    ax.set_ylim(-40, 50 if lvl == -70 else 20)
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("gain (dB)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8)

# Clean-only response must be flat apart from the EQ's fixed mid scoop.
x = noise * 10 ** (-20 / 20)
y = render(x, Gain=50, Balance=0)
f, H = transfer(x, y)
band = (f > 30) & (f < 100)
check(
    np.all(np.abs(db(H[band])) < 1.5),
    "clean path, flat EQ: 30-100 Hz within +/-1.5 dB (low end intact)",
)

# EQ curves with the drive out of the way (Balance 0).
ax = axes[0, 2]
for bass, treb in [(0, 0), (-12, 0), (12, 0), (0, -15), (0, 15), (12, 15)]:
    y = render(x, Gain=0, Balance=0, Bass=bass, Treble=treb)
    f, H = transfer(x, y)
    ax.semilogx(f[1:], db(H[1:]), label=f"Bass {bass:+d}, Treble {treb:+d}")
ax.set_title("EQ only (Balance 0%)")
ax.set_xlim(20, 20000)
ax.set_ylim(-20, 20)
ax.set_xlabel("frequency (Hz)")
ax.set_ylabel("gain (dB)")
ax.grid(True, which="both", alpha=0.3)
ax.legend(fontsize=8)

axes[1, 2].axis("off")
fig.savefig(f"{OUT}/freqresp.png", dpi=110)
print(f"  wrote {OUT}/freqresp.png")
finish()
