"""Silence in must give silence out, at every extreme setting."""

import itertools

import numpy as np

from fxtest import SR, check, db, finish, render

print("test_silence")
x = np.zeros(3 * SR)
n = 0
for drive, pres, level, blend, eq, shift in itertools.product(
        (0, 100), (0, 100), (0, 12), (0, 50, 100), (-12, 12), (0, 1)):
    y = render(x, Drive=drive, Presence=pres, Level=level, Blend=blend,
               Bass=eq, Mid=eq, Treble=eq, **{"Bass Shift": shift, "Mid Shift": shift})
    n += 1
    peak = np.max(np.abs(y)) if len(y) else 0.0
    if peak > 1e-6 or not np.all(np.isfinite(y)):
        check(False, f"silence D={drive} P={pres} L={level} B={blend} eq={eq} shift={shift}: "
                     f"peak {db(peak):.1f} dBFS")
        break
else:
    check(True, f"silence in gives < -120 dBFS out at {n} setting combinations")
finish()
