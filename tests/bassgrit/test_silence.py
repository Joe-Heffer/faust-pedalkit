# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Silence in must give silence out, at every extreme setting."""

import itertools

import numpy as np

from fxtest import SR, check, db, finish, render

print("test_silence")
x = np.zeros(3 * SR)
for dist, level, blend, xover in itertools.product((0, 100), (-40, 12), (0, 100), (40, 400)):
    y = render(x, Distortion=dist, Level=level, **{"Low Blend": blend}, Crossover=xover)
    peak = np.max(np.abs(y)) if len(y) else 0.0
    if peak > 1e-6 or not np.all(np.isfinite(y)):
        check(False, f"silence D={dist} L={level} B={blend} X={xover}: peak {db(peak):.1f} dBFS")
        break
else:
    check(True, "silence in gives < -120 dBFS out at 16 setting combinations")
finish()
