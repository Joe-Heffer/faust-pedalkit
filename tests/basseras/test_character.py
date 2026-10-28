# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Character: the targets from docs/basseras/design-notes.md, section 5.

1. Small-signal, the Character EQ is a mid peak or cut that glides with the
   knob: -15 dB near 250 Hz at 0, flat at 50, +15 dB near 700 Hz at 100.
   Measured as the response at each setting over the response at 50, less
   the extra broadband gain Character adds above noon (12 dB at 100).
2. That gain at each setting's own centre rises monotonically, spanning at
   least 20 dB from 0 to 100.
3. Above noon Character adds drive: at the default Drive, THD of a -12 dBFS
   110 Hz tone rises by at least 6 dB from Character 50 to 100.
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

print("test_character")
rng = np.random.default_rng(5)
x = rng.normal(0, 1, 8 * SR) * 10 ** (-70 / 20)
# Drive 0, Bite 0 and the speaker sim bypassed leave the Character EQ, the
# extra gain and fixed filters that cancel in the ratio.
BASE = dict(Drive=0, Bite=0, Blend=100, **{"Cab Bypass": 1})
SETTINGS = (0, 25, 50, 75, 100)
rows = []


def centre(c):
    """The chosen Character centre: 250 Hz to 700 Hz, log-uniform."""
    return 250 * (700 / 250) ** (c / 100)


f, H50 = transfer(x, render(x, Character=50, **BASE))
fig, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
ax = axes[0]
at_centre = []
for c in SETTINGS:
    _, H = transfer(x, render(x, Character=c, **BASE))
    extra = 12 * max(0, 2 * c / 100 - 1)
    rel = db(H) - db(H50) - extra
    ax.semilogx(f[1:], rel[1:], label=f"Character {c}% (less {extra:.0f} dB gain)")
    idx = np.unique(
        np.geomspace(np.searchsorted(f, 20), np.searchsorted(f, 20000), 200).astype(int)
    )
    rows.extend(("eq", c, f[i], rel[i]) for i in idx)
    want = 15 * (2 * c / 100 - 1)
    at_centre.append(rel[np.argmin(np.abs(f - centre(c)))])
    if c == 50:
        dev = np.max(np.abs(rel[(f > 30) & (f < 15000)]))
        check(dev < 0.1, f"Character 50: reference, {dev:.3f} dB")
        continue
    band = (f > 80) & (f < 4000)
    k = np.argmax(np.sign(want) * rel[band])
    fpk, gpk = f[band][k], rel[band][k]
    check(
        abs(np.log2(fpk / centre(c))) < 0.25 and abs(gpk - want) < 1,
        f"Character {c}: extreme {gpk:+.1f} dB at {fpk:.0f} Hz "
        f"(want {want:+.1f} dB at {centre(c):.0f} Hz)",
    )
ax.set_title("Character EQ relative to 50% (Drive 0%, -70 dBFS)")
ax.set_xlim(20, 20000)
ax.set_ylim(-20, 20)
ax.set_xlabel("frequency (Hz)")
ax.set_ylabel("gain relative to Character 50% (dB)")
ax.grid(True, which="both", alpha=0.3)
ax.legend(fontsize=8)

steps = np.diff(at_centre)
span = at_centre[-1] - at_centre[0]
check(
    np.all(steps > 0) and span >= 20,
    f"gain at each centre rises monotonically, spanning {span:.1f} dB (>= 20 dB)",
)

# Drive against Character: THD of 110 Hz at -12 dBFS, at three Drive settings.
ax = axes[1]
chars = np.arange(0, 101, 10)
thd = {}
for d in (0, 30, 60):
    vals = []
    for c in chars:
        hk = harmonics(render(sine(110, 2, -12), Drive=d, Character=c), 110, 10)
        vals.append(db(np.sqrt(np.sum(hk[1:] ** 2)) / hk[0]))
    thd[d] = np.array(vals)
    rows.extend(("thd", int(c), d, v) for c, v in zip(chars, vals, strict=True))
    ax.plot(chars, vals, "o-", label=f"Drive {d}%")
rise = thd[30][chars == 100][0] - thd[30][chars == 50][0]
check(rise >= 6, f"Drive 30: THD rises {rise:.1f} dB from Character 50 to 100 (>= 6 dB)")
ax.set_title("THD of 110 Hz, -12 dBFS in")
ax.set_xlabel("Character (%)")
ax.set_ylabel("THD (dB)")
ax.grid(True, alpha=0.3)
ax.legend()

save_plot(fig, "character")
# Long format: for "eq", x is frequency in hertz and the value the gain in dB
# relative to Character 50; for "thd", x is the Drive and the value THD in dB.
write_csv("character", ("test", "character", "x", "value_db"), rows)
finish()
