"""Silence in must give silence out, at every extreme setting."""

import itertools

import numpy as np

from fxtest import SR, check, db, finish, render

print("test_silence")
x = np.zeros(3 * SR)
for gain, level, bal, bass, treb in itertools.product(
    (0, 100), (0, 12), (0, 50, 100), (-12, 12), (-15, 15)
):
    y = render(x, Gain=gain, Level=level, Balance=bal, Bass=bass, Treble=treb)
    peak = np.max(np.abs(y)) if len(y) else 0.0
    if peak > 1e-6 or not np.all(np.isfinite(y)):
        check(
            False,
            f"silence G={gain} L={level} B={bal} lo={bass} hi={treb}: peak {db(peak):.1f} dBFS",
        )
        break
else:
    check(True, "silence in gives < -120 dBFS out at 48 setting combinations")
finish()
