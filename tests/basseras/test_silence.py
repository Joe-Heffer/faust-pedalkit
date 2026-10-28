# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Silence in must give silence out, at every extreme setting."""

import itertools

import numpy as np

from fxtest import SR, check, db, finish, render

print("test_silence")
x = np.zeros(3 * SR)
n = 0
for drive, char, level, blend, eq, bite, cab in itertools.product(
    (0, 100), (0, 50, 100), (0, 12), (0, 50, 100), (-12, 12), (0, 100), (0, 1)
):
    y = render(
        x,
        Drive=drive,
        Character=char,
        Level=level,
        Blend=blend,
        Low=eq,
        Mid=eq,
        High=eq,
        Bite=bite,
        **{"Cab Bypass": cab},
    )
    n += 1
    peak = np.max(np.abs(y)) if len(y) else 0.0
    if peak > 1e-6 or not np.all(np.isfinite(y)):
        check(
            False,
            f"silence D={drive} C={char} L={level} B={blend} eq={eq} bite={bite} cab={cab}: "
            f"peak {db(peak):.1f} dBFS",
        )
        break
else:
    check(True, f"silence in gives < -120 dBFS out at {n} setting combinations")
finish()
