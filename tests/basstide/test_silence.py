# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Silence in must give silence out, at every extreme setting."""

import itertools

import numpy as np

from fxtest import SR, check, db, finish, render

print("test_silence")
x = np.zeros(3 * SR)
combos = list(itertools.product((0, 100), (0, 100), (-90, 90), (0, 100), (-20, 12)))
for sweep, follow, feedback, depth, level in combos:
    y = render(x, Sweep=sweep, Follow=follow, Feedback=feedback, Depth=depth, Level=level, Rate=5)
    peak = np.max(np.abs(y)) if len(y) else 0.0
    if peak > 1e-6 or not np.all(np.isfinite(y)):
        check(
            False,
            f"silence S={sweep} Follow={follow} Fb={feedback} D={depth} L={level}: "
            f"peak {db(peak):.1f} dBFS",
        )
        break
else:
    check(True, f"silence in gives < -120 dBFS out at {len(combos)} setting combinations")
finish()
