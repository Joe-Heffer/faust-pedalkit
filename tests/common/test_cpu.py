# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""CPU use per instance stays low, including after the input falls silent.

The renderer times compute() alone, in 64-sample blocks as a live setup would
use, best of five passes. Two signals:

* live: uniform noise, the most work per sample the DSP can be given
* tail: one second of the same noise, then nine of silence

The tail is timed without flush-to-zero, as a host that leaves the FPU alone
would run an LV2 plug-in. If a decaying filter state reaches subnormal floats,
each operation on it is many times slower, so an instance on a silent track
can cost more than one that is playing. The Makefile's FAUSTFLAGS (-ftz 1)
prevents this; the check catches an effect, or a build, where it does not.

The figures depend on the machine and are written to cpu.csv for comparison.
The checks have wide margins so that a slow CI runner still passes.
"""

import numpy as np

from fxtest import SR, bench, check, controls, finish, write_csv

print("test_cpu")

# Chosen: 20 times faster than real time is 5 % of one core per instance at
# 48 kHz, so a dozen instances fit in a live set with room for the host. The
# existing effects measure 40 to 70 times on a 2020s laptop core.
MIN_REALTIME = 20
# Chosen: silence may cost at most this many times live signal. The existing
# effects measure 0.8 to 1.5 with -ftz 1, and 20 to 30 without it.
MAX_TAIL_RATIO = 3

ctl = controls()
SETTINGS = {"defaults": {}, "all maximum": {c["label"]: c["max"] for c in ctl}}

rng = np.random.default_rng(5)
live = rng.uniform(-0.3, 0.3, 10 * SR)
tail = np.concatenate([live[:SR], np.zeros(9 * SR)])

rows = []
for name, params in SETTINGS.items():
    ns_live, rt_live = bench(live, **params)
    ns_tail, rt_tail = bench(tail, **params)
    ns_ftz, rt_ftz = bench(tail, ftz=True, **params)
    for signal, ftz, ns, rt in (
        ("live", 0, ns_live, rt_live),
        ("tail", 0, ns_tail, rt_tail),
        ("tail", 1, ns_ftz, rt_ftz),
    ):
        rows.append((name, signal, ftz, 64, ns, rt, 100 / rt))
    check(
        rt_live >= MIN_REALTIME,
        f"{name}: {rt_live:.0f}x real time on live signal, "
        f"{100 / rt_live:.1f} % of a core at 48 kHz",
    )
    ratio = ns_tail / ns_live
    check(
        ratio <= MAX_TAIL_RATIO,
        f"{name}: a decaying tail costs {ratio:.2f}x live signal without flush-to-zero "
        f"({ns_tail / ns_ftz:.2f}x the cost with it)",
    )

write_csv(
    "cpu",
    ("setting", "signal", "ftz", "block", "ns_per_sample", "realtime_factor", "core_percent_48k"),
    rows,
)
finish()
