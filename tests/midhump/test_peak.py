# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""No output sample may exceed 0 dBFS, even with every control at maximum."""

import numpy as np

from fxtest import SR, check, db, finish, log_sweep, render

print("test_peak")
rng = np.random.default_rng(1)
t = np.arange(4 * SR) / SR
signals = {
    "0 dBFS 41 Hz square": np.sign(np.sin(2 * np.pi * 41.2 * t)),
    "0 dBFS clipped noise": np.clip(rng.normal(0, 1, len(t)), -1, 1),
    "0 dBFS sweep 41 Hz-20 kHz": log_sweep(41.2, 20000, 4, 0)[0],
    "0 dBFS impulse train": (np.arange(len(t)) % 4800 == 0).astype(float),
}

worst = -np.inf
for name, x in signals.items():
    for blend in (0, 50, 100):
        for bloom in (0, 100):
            y = render(x, Level=12, Drive=100, Tone=100, Blend=blend, Bloom=bloom)
            peak = np.max(np.abs(y))
            worst = max(worst, db(peak))
            check(
                peak <= 1.0 and np.all(np.isfinite(y)),
                f"{name}, Blend {blend}, Bloom {bloom}: peak {db(peak):+.2f} dBFS",
            )
print(f"  worst-case peak {worst:+.3f} dBFS")
finish()
