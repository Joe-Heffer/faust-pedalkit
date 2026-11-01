# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""The measurable targets from docs/basstide/design-notes.md, section 5.

2. The low band is untouched while the comb sweeps.
3. The wet tap passes through zero: ahead of the dry and behind it.
4. The notches are deep.
5. With Follow 100, each note throws the sweep out behind the dry ...
6. ... and it glides back to the zero point.
7. A soft note moves it much less than a loud one.

The wet tap is found from the difference between Depth 100 and Depth 0
renders of the same input, which is half of (wet - dry high band). Its
short-time impulse response has a negative tap at the dry delay and a
positive one at the wet delay.
"""

import numpy as np

from fxtest import SR, check, db, finish, plt, render, save_plot, transfer, write_csv

print("test_targets")

# Repeated from src/basstide.dsp, so a change there fails this test.
ZERO_SAMPLES = 96
LEAD_MAX = ZERO_SAMPLES - 2
LAG_MAX = round(0.008 * SR)
# Chosen: below this the wet and dry taps have cancelled (wet at the zero
# point), and the window counts as at rest.
TAP_MIN = 0.1

rng = np.random.default_rng(11)


def short_time_ir(x, y, win_s, hop_s, nfft):
    """(centre times, impulse responses) of y against x in short windows."""
    m, hop = int(win_s * SR), int(hop_s * SR)
    w = np.hanning(nfft)
    times, irs = [], []
    for s in range(0, len(x) - m, hop):
        sxy = np.zeros(nfft // 2 + 1, complex)
        sxx = np.zeros(nfft // 2 + 1)
        for i in range(s, s + m - nfft, nfft // 4):
            X = np.fft.rfft(w * x[i : i + nfft])
            sxy += np.fft.rfft(w * y[i : i + nfft]) * np.conj(X)
            sxx += np.abs(X) ** 2
        irs.append(np.fft.irfft(sxy / np.maximum(sxx, 1e-30), nfft))
        times.append((s + m / 2) / SR)
    return np.array(times), np.array(irs)


def wet_offsets(x, win_s, hop_s, nfft=2048, **params):
    """Wet-tap offset from the dry tap, in samples, in each window (0 at rest)."""
    y1 = render(x, Depth=100, **params)
    y0 = render(x, Depth=0, **params)
    t, irs = short_time_ir(x, y1 - y0, win_s, hop_s, nfft)
    offs = np.zeros(len(t))
    for i, h in enumerate(irs):
        h = h[: ZERO_SAMPLES + LAG_MAX + 32].copy()
        k = int(np.argmax(h))
        offs[i] = k - ZERO_SAMPLES if h[k] > TAP_MIN else 0.0
    return t, offs


rows = []
fig, axes = plt.subplots(1, 3, figsize=(17, 5), constrained_layout=True)

# 2. The low band is untouched while the LFO sweeps the comb.
lfo = {"Follow": 0, "Sweep": 100, "Rate": 0.2, "Feedback": 0}
xn = rng.normal(0, 10 ** (-30 / 20), 10 * SR)
f, H1 = transfer(xn, render(xn, Depth=100, **lfo))
_, H0 = transfer(xn, render(xn, Depth=0, **lfo))
low = (f > 30) & (f < 80)
dev = np.max(np.abs(db(H1[low]) - db(H0[low])))
check(dev < 0.5, f"LFO sweeping: 30-80 Hz within {dev:.2f} dB of Depth 0 (< 0.5)")

# 3. Through zero, over two LFO cycles.
t, offs = wet_offsets(xn, 0.25, 0.05, **lfo)
ahead, behind = -np.min(offs), np.max(offs)
check(ahead >= 80, f"LFO: wet tap reaches {ahead:.0f} samples ahead of the dry (>= 80)")
check(behind >= 330, f"LFO: wet tap reaches {behind:.0f} samples behind the dry (>= 330)")
rows.extend(("lfo", "-30", tt, o) for tt, o in zip(t, offs, strict=True))
ax = axes[0]
ax.plot(t, offs)
ax.axhline(0, color="k", lw=0.8)
ax.axhline(-LEAD_MAX, color="k", ls=":", lw=0.8)
ax.axhline(LAG_MAX, color="k", ls=":", lw=0.8)
ax.set_title("LFO, Rate 0.2 Hz, Sweep 100%: wet tap against the dry")
ax.set_xlabel("time (s)")
ax.set_ylabel("wet minus dry delay (samples)")

# 4. The notches are deep, near the lag end of the sweep where it moves least.
ys = render(xn, Depth=100, **lfo)
m = int(0.25 * SR)
worst = 0.0
for tt, o in zip(t, offs, strict=True):
    if o < 200:
        continue
    s = int(tt * SR) - m // 2
    fw, Hw = transfer(xn[s : s + m], ys[s : s + m], nfft=4096)
    band = (fw > 400) & (fw < 2000)
    worst = min(worst, np.min(db(Hw[band])))
check(worst <= -25, f"LFO: deepest notch 400 Hz-2 kHz {worst:.1f} dB (<= -25)")

# 5 to 7. Follow mode: a noise burst from silence at two levels.
glide = 0.4
onset = 0.5
ax = axes[1]
peaks = {}
for lvl in (-15, -40):
    xb = np.concatenate([np.zeros(int(onset * SR)), rng.normal(0, 10 ** (lvl / 20), 3 * SR)])
    tb, ob = wet_offsets(
        xb, 0.1, 0.025, nfft=1024, Follow=100, Sweep=100, Glide=1000 * glide, Feedback=0
    )
    tb = tb - onset
    peaks[lvl] = (np.max(ob), tb[int(np.argmax(ob))])
    rows.extend(("follow", str(lvl), tt, o) for tt, o in zip(tb, ob, strict=True))
    ax.plot(tb, ob, label=f"{lvl} dBFS noise")
    if lvl == -15:
        late = np.max(np.abs(ob[tb >= 3 * glide]))
        check(late <= 20, f"Follow: {late:.0f} samples from the dry at 3 x Glide (<= 20)")
big, t_big = peaks[-15]
check(big >= 250, f"Follow, -15 dBFS onset: wet tap thrown {big:.0f} samples behind (>= 250)")
check(
    0.2 * glide <= t_big <= 0.8 * glide,
    f"Follow: furthest point {1000 * t_big:.0f} ms after the onset "
    f"({1000 * 0.2 * glide:.0f} to {1000 * 0.8 * glide:.0f})",
)
soft = peaks[-40][0]
check(soft < 60, f"Follow, -40 dBFS onset: wet tap moves {soft:.0f} samples (< 60)")
ax.axvline(0, color="k", lw=0.8)
ax.set_title(f"Follow 100%, Glide {1000 * glide:.0f} ms: wet tap after an onset")
ax.set_xlabel("time after onset (s)")
ax.set_ylabel("wet minus dry delay (samples)")
ax.legend()

ax = axes[2]
ax.semilogx(f[1:], db(H1[1:]), lw=0.6, label="Depth 100 (LFO, averaged)")
ax.semilogx(f[1:], db(H0[1:]), lw=0.8, label="Depth 0")
ax.set_xlim(20, 20000)
ax.set_ylim(-30, 10)
ax.set_title("Average response with the LFO sweeping")
ax.set_xlabel("frequency (Hz)")
ax.set_ylabel("gain (dB)")
ax.legend()

for a in axes:
    a.grid(True, which="both", alpha=0.3)
save_plot(fig, "targets")
write_csv("targets_wet_tap", ("mode", "input_dbfs", "time_s", "offset_samples"), rows)
finish()
