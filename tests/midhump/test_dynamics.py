# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Bloom: the bias-shift targets from docs/midhump/design-notes.md, section 5.

Bloom moves the diodes' operating point by an amount that charges up on loud
playing and discharges afterwards, so these tests look at harmonics over time
rather than at a steady state:

9.  Bloom changes nothing while the clipper's branch stays below its knee
    (a -40 dBFS tone at any Drive).
10. On a loud tone, Bloom 100 adds strong second harmonic that Bloom 0 lacks.
11. The second harmonic builds up over tens of milliseconds after the onset.
12. It outlasts the loud passage, then dies away within a second.
13. The cleanup curve: H2 appears only above the knee, and rises with level.
14. 4x oversampling still keeps aliases low with Bloom at 100.
"""

import os

import numpy as np

from fxtest import (
    OUT,
    RENDER,
    RENDER_1X,
    SR,
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
    sine,
    write_csv,
    write_wav,
)

print("test_dynamics")

F0 = 220
QUIET, LOUD = -40, -12
T_ON, T_LOUD, T_TAIL = 0.3, 0.6, 1.4  # seconds: quiet lead-in, loud, quiet tail
x = burst(F0, [-80, LOUD, QUIET], [T_ON, T_LOUD, T_TAIL])
t_off = T_ON + T_LOUD


HALF_WIN = 2 / F0  # half of the four-period analysis window, in seconds


def h2_rel(y):
    """H2 relative to H1 in dB over time, with a window of four periods."""
    t, a = harmonics_over_time(y, F0, n=3)
    return t, db(a[:, 2]) - db(a[:, 1])


def at(t, r, s):
    return r[np.argmin(np.abs(t - s))]


fig, axes = plt.subplots(1, 3, figsize=(16, 5), constrained_layout=True)
rows = []

# 9. Transparent below the knee: a quiet tone alone, Bloom 0 against 100.
q = sine(F0, 2, QUIET)
for d in (0, 50, 100):
    diff = np.max(np.abs(render(q, Drive=d, Bloom=100) - render(q, Drive=d, Bloom=0)))
    check(diff == 0, f"Drive {d}: Bloom has no effect on a {QUIET} dBFS tone (max diff {diff:.1e})")

# 10 to 12. Quiet, loud, quiet: H2/H1 over time.
ax = axes[0]
tracks = {}
for d in (50, 100):
    for b in (0, 50, 100):
        t, r = h2_rel(render(x, Drive=d, Bloom=b))
        tracks[(d, b)] = r
        rows.extend(
            ("burst", d, b, "H2", round(ti, 4), ri) for ti, ri in zip(t[::4], r[::4], strict=True)
        )
        if d == 50:
            ax.plot(t, r, label=f"Drive {d}, Bloom {b}")
ax.axvspan(T_ON, t_off, color="0.9", zorder=0, label="loud section")
ax.set_title(f"{F0} Hz: {LOUD} dBFS for {T_LOUD} s, then {QUIET} dBFS")
ax.set_xlabel("time (s)")
ax.set_ylabel("H2 relative to H1 (dB)")
ax.set_ylim(-100, 0)
ax.grid(True, alpha=0.3)
ax.legend(fontsize=8)

for d in (50, 100):
    r0, r1 = tracks[(d, 0)], tracks[(d, 100)]
    steady0 = at(t, r0, t_off - 0.05)
    steady1 = at(t, r1, t_off - 0.05)
    check(
        steady1 > -35 and steady1 - steady0 > 30,
        f"Drive {d}: loud H2 {steady1:.1f} dBc at Bloom 100 against {steady0:.1f} at Bloom 0 "
        "(> -35 dBc and > 30 dB more)",
    )
    # Build-up: the first window lying wholly after the onset that is within
    # 3 dB of the steady value, timed at its centre. A window straddling the
    # onset reads the step itself as H2, so those are skipped. The window (four
    # periods, 18 ms) blurs the timing, so the bounds are loose around
    # bloomAtt (15 ms).
    after = (t - HALF_WIN >= T_ON) & (t < t_off)
    rise = t[after][np.argmax(r1[after] >= steady1 - 3)] - T_ON
    check(0.01 <= rise <= 0.1, f"Drive {d}: H2 builds up in {1000 * rise:.0f} ms (10 ms to 100 ms)")
    tail0, tail1 = at(t, r0, t_off + 0.1), at(t, r1, t_off + 0.1)
    check(
        tail1 - tail0 > 20,
        f"Drive {d}: 100 ms after the loud section, H2 {tail1:.1f} dBc against {tail0:.1f} "
        "(> 20 dB more)",
    )
    late = at(t, r1, t_off + 1.2)
    check(late < -60, f"Drive {d}: 1.2 s after, H2 has died away to {late:.1f} dBc (< -60)")

# 13. Cleanup curve: steady-state H2 and H3 against input level, Drive 50.
ax = axes[1]
levels = np.arange(-50, 1, 2.5)
traj = {b: harmonic_trajectory(F0, levels, n=3, Drive=50, Bloom=b) for b in (0, 100)}
for b, h in traj.items():
    for k, style in ((2, "-"), (3, "--")):
        rel = db(h[:, k - 1]) - db(h[:, 0])
        ax.plot(levels, rel, style, label=f"H{k}, Bloom {b}")
        rows.extend(("cleanup", 50, b, f"H{k}", lv, v) for lv, v in zip(levels, rel, strict=True))
ax.set_title(f"Cleanup curve, {F0} Hz, Drive 50%")
ax.set_xlabel("input level (dBFS)")
ax.set_ylabel("dB relative to H1")
ax.set_ylim(-140, 0)
ax.grid(True, alpha=0.3)
ax.legend(fontsize=8)
h2 = db(traj[100][:, 1]) - db(traj[100][:, 0])
quiet_h2 = np.max(h2[levels <= -40])
check(quiet_h2 < -80, f"Bloom 100: no H2 below -40 dBFS input (max {quiet_h2:.1f} dBc, < -80)")
check(np.max(h2) > -30, f"Bloom 100: H2 reaches {np.max(h2):.1f} dBc at playing level (> -30)")

# A plucked note, the case a player hears. The measurement uses a pure
# decaying sine (n=1), so any H2 comes from the effect; the WAVs use a pluck
# with its own harmonics, for listening.
ax = axes[2]
p1 = pluck(110, 2.0, LOUD, decay=0.4, n=1)
p8 = pluck(110, 2.0, LOUD, decay=0.4)
peak_t = {}
for b in (0, 100):
    t2, a2 = harmonics_over_time(render(p1, Drive=50, Bloom=b), 110, n=3)
    r2 = db(a2[:, 2]) - db(a2[:, 1])
    ax.plot(t2, r2, label=f"H2, Bloom {b}")
    rows.extend(
        ("pluck", 50, b, "H2", round(ti, 4), ri) for ti, ri in zip(t2[::4], r2[::4], strict=True)
    )
    whole = t2 - 2 / 110 >= 0  # windows lying wholly after the onset
    peak_t[b] = t2[whole][np.argmax(r2[whole])]
    write_wav(os.path.join(OUT, f"pluck-bloom{b}.wav"), render(p8, Drive=50, Bloom=b))
# H2 peaks once the bias has charged, not on the first cycle of the attack.
check(
    peak_t[100] > 0.03,
    f"Pluck, Bloom 100: H2 peaks {1000 * peak_t[100]:.0f} ms into the note (> 30 ms)",
)
ax.set_title("110 Hz pluck, Drive 50%")
ax.set_xlabel("time (s)")
ax.set_ylabel("H2 relative to H1 (dB)")
ax.set_ylim(-100, 0)
ax.grid(True, alpha=0.3)
ax.legend(fontsize=8)


# 14. Aliasing with the bias moving: 1.1 kHz at Drive 100, Bloom 100.
def worst_alias(binary, f0=1100):
    y = render(sine(f0, 3, LOUD), binary=binary, Drive=100, Tone=100, Bloom=100)
    spec = np.abs(np.fft.rfft(y[-SR:] * np.hanning(SR)))
    spec /= spec[f0]
    harm = np.zeros(len(spec), bool)
    for k in range(1, int((SR / 2) // f0) + 1):
        harm[max(k * f0 - 3, 0) : k * f0 + 4] = True
    harm[:20] = True
    return db(np.max(np.where(harm, 0.0, spec)))


if os.path.exists(RENDER_1X):
    a4, a1 = worst_alias(RENDER), worst_alias(RENDER_1X)
    check(a4 < -60, f"Bloom 100, 1100 Hz: worst alias with 4x {a4:.1f} dBc (< -60), 1x {a1:.1f}")
    rows.extend((("alias", 100, 100, "4x", 1100, a4), ("alias", 100, 100, "1x", 1100, a1)))

save_plot(fig, "dynamics")
# Long format. x is time in seconds for "burst", input level in dBFS for
# "cleanup" and frequency in hertz for "alias"; value is in dB (dBc).
write_csv("dynamics", ("test", "drive", "bloom", "series", "x", "value_db"), rows)
finish()
