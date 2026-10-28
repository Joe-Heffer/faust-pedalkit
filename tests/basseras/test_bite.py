# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Bite: a subsonic high-pass before the clippers and a presence peak after
them (docs/basseras/design-notes.md, section 5).

1. Bite 100 over Bite 0, small signal: at least 12 dB less at 15 Hz and 6 dB
   less at 25 Hz, within 1 dB at 100 to 500 Hz, and a peak of +4 to +8 dB
   between 1.5 and 4 kHz.
2. Bite 50 lies between the two (it is continuous, unlike the pedal's switch).
3. The tightening: the subsonic filter keeps rumble out of the clippers. With
   a 15 Hz tone at -12 dBFS under a 220 Hz note at -24 dBFS, at full Drive,
   the intermodulation sidebands at 205 and 235 Hz fall by at least 10 dB.
"""

import numpy as np

from fxtest import SR, check, db, finish, plt, render, save_plot, sine, transfer, write_csv

print("test_bite")
rng = np.random.default_rng(3)
x = rng.normal(0, 1, 8 * SR) * 10 ** (-70 / 20)
BASE = dict(Drive=0, Blend=100)
rows = []


def at(f, r, hz):
    return r[np.argmin(np.abs(f - hz))]


f, H0 = transfer(x, render(x, Bite=0, **BASE))
fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
curves = {}
for b in (25, 50, 75, 100):
    _, H = transfer(x, render(x, Bite=b, **BASE))
    curves[b] = db(H) - db(H0)
    ax.semilogx(f[1:], curves[b][1:], label=f"Bite {b}%")
    idx = np.unique(
        np.geomspace(np.searchsorted(f, 10), np.searchsorted(f, 20000), 200).astype(int)
    )
    rows.extend((b, f[i], curves[b][i]) for i in idx)

r = curves[100]
check(at(f, r, 15) <= -12, f"Bite 100: {at(f, r, 15):.1f} dB at 15 Hz (<= -12 dB)")
check(at(f, r, 25) <= -6, f"Bite 100: {at(f, r, 25):.1f} dB at 25 Hz (<= -6 dB)")
mid = r[(f > 100) & (f < 500)]
check(np.max(np.abs(mid)) < 1, f"Bite 100: within {np.max(np.abs(mid)):.2f} dB from 100 to 500 Hz")
band = (f > 1500) & (f < 4000)
pk, fpk = np.max(r[band]), f[band][np.argmax(r[band])]
check(4 <= pk <= 8, f"Bite 100: presence peak {pk:+.1f} dB at {fpk:.0f} Hz (+4 to +8 dB)")
m50 = at(f, curves[50], fpk)
check(0 < m50 < pk, f"Bite 50: {m50:+.1f} dB at {fpk:.0f} Hz, between Bite 0 and 100")
ax.set_title("Bite relative to Bite 0% (Drive 0%, -70 dBFS)")
ax.set_xlim(10, 20000)
ax.set_ylim(-30, 10)
ax.set_xlabel("frequency (Hz)")
ax.set_ylabel("gain relative to Bite 0% (dB)")
ax.grid(True, which="both", alpha=0.3)
ax.legend()

# The tightening: rumble modulating a note at full Drive. Whole-hertz tones
# over a one-second window put every product on its own FFT bin.
x2 = sine(15, 3, -12) + sine(220, 3, -24)
imd = {}
for b in (0, 100):
    s = np.abs(np.fft.rfft(render(x2, Drive=100, Blend=100, Bite=b)[-SR:]))
    imd[b] = db((s[205] + s[235]) / 2 / s[220])
    rows.append((b, "imd", imd[b]))
check(
    imd[0] - imd[100] >= 10,
    f"Drive 100: rumble sidebands {imd[0]:.1f} dBc at Bite 0, {imd[100]:.1f} dBc at Bite 100 "
    "(>= 10 dB less)",
)

save_plot(fig, "bite")
# Long format: x is frequency in hertz, or "imd" for the sideband level (dBc).
write_csv("bite", ("bite", "x", "value_db"), rows)
finish()
