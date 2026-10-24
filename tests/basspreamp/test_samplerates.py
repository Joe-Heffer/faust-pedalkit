# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Output stays finite, at or below 0 dBFS and near its 48 kHz level at every sample rate.

Hosts and validators (clap-validator's process-varying-sample-rates) run the
plugin from 8 kHz up. A filter prewarped above Nyquist turns unstable there.
"""

import numpy as np

from fxtest import check, db, finish, render, write_csv

print("test_samplerates")
RATES = (8000, 11025, 16000, 22050, 32000, 44100, 48000, 88200, 96000, 192000)
SETTINGS = {
    "default": {},
    "max": dict(
        Drive=100,
        Presence=100,
        Level=12,
        Blend=100,
        Bass=12,
        Mid=12,
        Treble=12,
        **{"Bass Shift": 1, "Mid Shift": 1},
    ),
    "clean": dict(Drive=0, Presence=0, Blend=0, Bass=-12, Mid=-12, Treble=-12),
}


def rms_db(y):
    return db(np.sqrt(np.mean(y**2)))


rows = []
for name, params in SETTINGS.items():
    levels = {}
    for sr in RATES:
        t = np.arange(sr) / sr
        y = render(10 ** (-12 / 20) * np.sin(2 * np.pi * 110 * t), sr=sr, **params)
        finite = bool(np.all(np.isfinite(y)))
        peak = float(np.max(np.abs(y))) if finite else float("nan")
        levels[sr] = rms_db(y[sr // 2 :]) if finite else float("nan")
        rows.append((name, sr, int(finite), db(peak) if finite else "", levels[sr]))
        check(finite, f"{name} at {sr} Hz: output is finite")
        if finite:
            check(peak <= 1.0, f"{name} at {sr} Hz: peak {db(peak):+.2f} dBFS")
    for sr in RATES:
        dev = levels[sr] - levels[48000]
        check(abs(dev) < 6, f"{name} at {sr} Hz: 110 Hz level {dev:+.2f} dB from 48 kHz")

write_csv("samplerates", ("setting", "sample_rate_hz", "finite", "peak_dbfs", "rms_dbfs"), rows)
finish()
