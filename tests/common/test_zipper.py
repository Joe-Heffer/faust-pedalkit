# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""No control clicks or zippers when a host jumps it from one end to the other.

A host applies automation, preset changes and MIDI-learnt knob moves as
abrupt steps between blocks. A control without smoothing (si.smoo) turns each
step into a discontinuity, which is a broadband click; a smoother that is too
fast does the same on a smaller scale.

For every control in turn, with the others at their defaults, a 110 Hz sine
runs while the host sets the control to its minimum, jumps it to its maximum
at 1 s and back at 2 s. A click shows as a burst of energy above HP_HZ that is
louder than the steady state on either side of the jump.
"""

import numpy as np

from fxtest import SR, check, controls, db, finish, plt, render, save_plot, sine, write_csv

print("test_zipper")

# Chosen: well above the low harmonics of a 110 Hz note, where a step's
# broadband click stands out.
HP_HZ = 8000
# Chosen: 5 ms windows resolve a click without averaging it away.
WIN = int(0.005 * SR)
# Chosen: a smoothed jump stays within 5 dB of the louder side wherever the
# burst is above FLOOR_DBFS (measured); an unsmoothed one overshoots by 20 dB
# or more.
MAX_EXCESS_DB = 6
# Chosen: bursts below this are inaudible, whatever they are relative to.
FLOOR_DBFS = -96

x = sine(110, 3.0, -12)

# Linear-phase high-pass: a 1023-tap Kaiser-windowed sinc (beta 12, stop band
# below -110 dB), so the 110 Hz fundamental itself stays under every effect's
# own high-frequency content. mode="same" removes its 511-sample delay.
_k = np.arange(1023) - 511
HP = -2 * HP_HZ / SR * np.sinc(2 * HP_HZ / SR * _k) * np.kaiser(1023, 12)
HP[511] += 1


def hf_envelope(y):
    """RMS level above HP_HZ in WIN-sample windows, in dBFS."""
    hf = np.convolve(y, HP, mode="same")
    n = len(hf) // WIN
    return db(np.sqrt(np.mean(hf[: n * WIN].reshape(n, WIN) ** 2, axis=1)))


def window(env, t0, t1):
    return env[int(t0 * SR / WIN) : int(t1 * SR / WIN)]


rows = []
summary = []
for c in controls():
    lo, hi = c["min"], c["max"]
    y = render(x, events=[(c["label"], hi, 1.0), (c["label"], lo, 2.0)], **{c["label"]: lo})
    if not np.all(np.isfinite(y)):
        check(False, f"{c['label']}: output is finite through the jumps")
        continue
    env = hf_envelope(y)
    # Steady state: before the first jump, and once the smoother has settled.
    at_lo = window(env, 0.5, 0.95).max()
    at_hi = window(env, 1.6, 1.95).max()
    at_lo2 = window(env, 2.6, 2.95).max()
    for direction, t, before, after in (("up", 1.0, at_lo, at_hi), ("down", 2.0, at_hi, at_lo2)):
        burst = window(env, t - 0.01, t + 0.15).max()
        excess = burst - max(before, after)
        ok = excess <= MAX_EXCESS_DB or burst < FLOOR_DBFS
        check(
            ok,
            f"{c['label']} {direction} ({lo:g} -> {hi:g}): burst {burst:.1f} dBFS, "
            f"{excess:+.1f} dB over the steady state",
        )
        rows.append((c["label"], direction, burst, max(before, after), excess))
        summary.append((f"{c['label']} {direction}", excess if burst >= FLOOR_DBFS else 0.0))

fig, ax = plt.subplots(figsize=(8, max(3, 0.35 * len(summary) + 1)))
labels = [s[0] for s in summary]
ax.barh(labels, [s[1] for s in summary])
ax.axvline(MAX_EXCESS_DB, color="r", ls="--", lw=1, label=f"limit ({MAX_EXCESS_DB} dB)")
ax.invert_yaxis()
ax.set(xlabel=f"burst above {HP_HZ / 1000:g} kHz over the steady state (dB)")
ax.set_title("Full-range control jumps under a 110 Hz sine")
ax.grid(alpha=0.3, axis="x")
ax.legend()
fig.tight_layout()
save_plot(fig, "zipper")
write_csv("zipper", ("control", "direction", "burst_dbfs", "steady_dbfs", "excess_db"), rows)
finish()
