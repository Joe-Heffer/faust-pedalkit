# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Dynamics and feel: the targets from docs/basseras/design-notes.md, section 6.

Above noon, Character lets hard notes push stage 1's bias off centre. The
bias charges after the attack and recovers afterwards, so these tests look at
the second harmonic over time:

1. Quiet, loud, quiet (110 Hz at -80, -12, -40 dBFS): at Character 100 the
   loud section carries H2 above -30 dBc, at least 30 dB more than at
   Character 50, where the clip stays symmetric.
2. H2 builds up over 10 to 150 ms after the onset, rather than appearing on
   the first cycle.
3. 100 ms after the loud section H2 is still at least 20 dB above Character
   50, and 1.1 s after it has died away below -60 dBc.
4. On a plucked note, H2 peaks more than 30 ms into the note.
5. Full Drive limits: from -20 to 0 dBFS in, the output rises by less than
   0.5 dB per dB (the manual's "limits transient peaks").
"""

import os

import numpy as np

from fxtest import (
    OUT,
    burst,
    check,
    db,
    finish,
    harmonic_trajectory,
    harmonics_over_time,
    plt,
    pluck,
    render,
    save_plot,
    write_csv,
    write_wav,
)

print("test_dynamics")

F0 = 110
QUIET, LOUD = -40, -12
T_ON, T_LOUD, T_TAIL = 0.3, 0.6, 1.4  # seconds: silent lead-in, loud, quiet tail
x = burst(F0, [-80, LOUD, QUIET], [T_ON, T_LOUD, T_TAIL])
t_off = T_ON + T_LOUD
HALF_WIN = 2 / F0  # half of the four-period analysis window, in seconds


def h2_rel(y, f0=F0):
    """H2 relative to H1 in dB over time, with a window of four periods."""
    t, a = harmonics_over_time(y, f0, n=3)
    return t, db(a[:, 2]) - db(a[:, 1])


def at(t, r, s):
    return r[np.argmin(np.abs(t - s))]


fig, axes = plt.subplots(1, 3, figsize=(16, 5), constrained_layout=True)
rows = []

# 1 to 3. Quiet, loud, quiet.
ax = axes[0]
tracks = {}
for c in (50, 75, 100):
    t, r = h2_rel(render(x, Character=c))
    tracks[c] = r
    rows.extend(("burst", c, "H2", round(ti, 4), ri) for ti, ri in zip(t[::4], r[::4], strict=True))
    ax.plot(t, r, label=f"Character {c}%")
ax.axvspan(T_ON, t_off, color="0.9", zorder=0, label="loud section")
ax.set_title(f"{F0} Hz: {LOUD} dBFS for {T_LOUD} s, then {QUIET} dBFS (Drive 30%)")
ax.set_xlabel("time (s)")
ax.set_ylabel("H2 relative to H1 (dB)")
ax.set_ylim(-120, 0)
ax.grid(True, alpha=0.3)
ax.legend(fontsize=8)

r0, r1 = tracks[50], tracks[100]
steady0, steady1 = at(t, r0, t_off - 0.05), at(t, r1, t_off - 0.05)
check(
    steady1 > -30 and steady1 - steady0 > 30,
    f"loud H2 {steady1:.1f} dBc at Character 100 against {steady0:.1f} at 50 "
    "(> -30 dBc, > 30 dB more)",
)
# The first window lying wholly after the onset that is within 3 dB of the
# steady value, timed at its centre.
after = (t - HALF_WIN >= T_ON) & (t < t_off)
rise = t[after][np.argmax(r1[after] >= steady1 - 3)] - T_ON
check(0.01 <= rise <= 0.15, f"H2 builds up in {1000 * rise:.0f} ms (10 to 150 ms)")
tail0, tail1 = at(t, r0, t_off + 0.1), at(t, r1, t_off + 0.1)
check(
    tail1 - tail0 > 20,
    f"100 ms after the loud section, H2 {tail1:.1f} dBc against {tail0:.1f} (> 20 dB more)",
)
late = at(t, r1, t_off + 1.1)
check(late < -60, f"1.1 s after, H2 has died away to {late:.1f} dBc (< -60)")

# 4. A plucked note. The measurement uses a pure decaying sine (n=1), so any
# H2 comes from the effect; the WAVs use a pluck with its own harmonics.
ax = axes[1]
p1 = pluck(F0, 2.0, LOUD, decay=0.4, n=1)
p8 = pluck(55, 2.0, LOUD, decay=0.6)
peak_t = {}
for c in (50, 100):
    t2, r2 = h2_rel(render(p1, Character=c))
    ax.plot(t2, r2, label=f"H2, Character {c}%")
    rows.extend(
        ("pluck", c, "H2", round(ti, 4), ri) for ti, ri in zip(t2[::4], r2[::4], strict=True)
    )
    whole = t2 - HALF_WIN >= 0
    peak_t[c] = t2[whole][np.argmax(r2[whole])]
for c in (0, 50, 100):
    write_wav(os.path.join(OUT, f"pluck-character{c}.wav"), render(p8, Character=c))
check(
    peak_t[100] > 0.03,
    f"pluck, Character 100: H2 peaks {1000 * peak_t[100]:.0f} ms into the note (> 30 ms)",
)
ax.set_title(f"{F0} Hz pluck, Drive 30%")
ax.set_xlabel("time (s)")
ax.set_ylabel("H2 relative to H1 (dB)")
ax.set_ylim(-120, 0)
ax.grid(True, alpha=0.3)
ax.legend(fontsize=8)

# 5. Output against input level, the fundamental of 110 Hz.
ax = axes[2]
levels = np.arange(-50, 1, 2.5)
for d in (0, 30, 100):
    out = db(harmonic_trajectory(F0, levels, n=1, Drive=d)[:, 0])
    ax.plot(levels, out, "o-", ms=3, label=f"Drive {d}%")
    rows.extend(("level", d, "H1", lv, v) for lv, v in zip(levels, out, strict=True))
    if d == 100:
        slope = (out[levels == 0][0] - out[levels == -20][0]) / 20
        check(
            slope < 0.5, f"Drive 100: output rises {slope:.2f} dB per dB from -20 to 0 dBFS (< 0.5)"
        )
ax.set_title(f"Output level of {F0} Hz against input (Character 50%)")
ax.set_xlabel("input level (dBFS)")
ax.set_ylabel("output fundamental (dBFS)")
ax.grid(True, alpha=0.3)
ax.legend(fontsize=8)

save_plot(fig, "dynamics")
# Long format. The second column is Character for "burst" and "pluck" and
# Drive for "level"; x is time in seconds, or input level in dBFS for "level".
write_csv("dynamics", ("test", "setting", "series", "x", "value_db"), rows)
finish()
