# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""After a hot input stops, the output decays to silence and stays finite.

Catches what a silence-in test cannot: a filter that self-oscillates or turns
unstable once driven hard, a limit cycle, or a DC offset that sticks. Each
setting gets two seconds of full-scale noise and then four of silence; the
last second must be below -120 dBFS.
"""

import numpy as np

from fxtest import SR, check, controls, db, finish, render

print("test_recovery")

ctl = controls()
SETTINGS = {
    "defaults": {},
    "all minimum": {c["label"]: c["min"] for c in ctl},
    "all maximum": {c["label"]: c["max"] for c in ctl},
}

rng = np.random.default_rng(7)
x = np.concatenate([np.clip(rng.normal(0, 0.5, 2 * SR), -1, 1), np.zeros(4 * SR)])
for name, params in SETTINGS.items():
    y = render(x, **params)
    finite = bool(np.all(np.isfinite(y)))
    check(finite, f"{name}: output is finite")
    if finite:
        rest = np.max(np.abs(y[-SR:]))
        check(rest < 1e-6, f"{name}: {db(rest):.1f} dBFS in the last second of silence")
finish()
