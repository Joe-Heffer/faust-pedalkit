# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Silence in must give silence out, at every extreme setting."""

import itertools

import numpy as np

from fxtest import SR, check, db, finish, render

print("test_silence")
x = np.zeros(3 * SR)
combos = list(itertools.product((0, 100), (0, 100), (-40, 12), (0, 100), (0, 100)))
for drive, tone, level, blend, bloom in combos:
    y = render(x, Drive=drive, Tone=tone, Level=level, Blend=blend, Bloom=bloom)
    peak = np.max(np.abs(y)) if len(y) else 0.0
    if peak > 1e-6 or not np.all(np.isfinite(y)):
        check(
            False,
            f"silence D={drive} T={tone} L={level} B={blend} Bl={bloom}: peak {db(peak):.1f} dBFS",
        )
        break
else:
    check(True, f"silence in gives < -120 dBFS out at {len(combos)} setting combinations")
finish()
