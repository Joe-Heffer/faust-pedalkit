# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Harmonic content at several Drive and Character settings, and the aliasing
benefit of 4x oversampling compared with a 1x build of the same DSP."""

import os

import numpy as np

from fxtest import (
    RENDER,
    RENDER_1X,
    SR,
    check,
    db,
    finish,
    harmonics,
    plt,
    render,
    save_plot,
    sine,
    write_csv,
)

print("test_harmonics")
fig, axes = plt.subplots(1, 3, figsize=(16, 5), constrained_layout=True)
harm_rows = []

# Harmonic spectra of A (110 Hz) at -12 dBFS: Drive at Character 50, then
# Character at the default Drive.
for ax, key, values, fixed in (
    (axes[0], "Drive", (0, 30, 100), {"Character": 50}),
    (axes[1], "Character", (0, 50, 100), {"Drive": 30}),
):
    f0, width = 110, 0.25
    for i, v in enumerate(values):
        p = {**fixed, key: v}
        y = render(sine(f0, 3, -12), **p)
        hk = harmonics(y, f0, 10)
        rel = db(hk / hk[0])
        harm_rows.extend((f0, p["Drive"], p["Character"], k + 1, rel[k]) for k in range(10))
        ax.bar(
            np.arange(1, 11) + (i - 1) * width, rel + 100, width, bottom=-100, label=f"{key} {v}%"
        )
        thd = np.sqrt(np.sum(hk[1:] ** 2)) / hk[0]
        print(
            f"  Drive {p['Drive']:3d}% Character {p['Character']:3d}%: THD {100 * thd:5.1f}%  "
            f"H2 {rel[1]:6.1f} dBc  H3 {rel[2]:6.1f} dBc"
        )
        if key == "Drive" and v == 100:
            check(thd > 0.2, f"Drive 100: THD {100 * thd:.1f}% (> 20 %)")
        if key == "Drive" and v == 0:
            check(thd < 0.02, f"Drive 0: THD {100 * thd:.2f}% (< 2 %, nearly clean)")
    others = ", ".join(f"{k} {v}%" for k, v in fixed.items())
    ax.set_title(f"Harmonics of {f0} Hz, -12 dBFS in, {others}")
    ax.set_xlabel("harmonic number")
    ax.set_ylabel("level relative to fundamental (dB)")
    ax.set_xticks(range(1, 11))
    ax.set_ylim(-100, 5)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend()


# Aliasing. With f0 a whole number of hertz that does not divide 48 kHz, the
# true harmonics and the aliases land on different FFT bins. Full Drive and
# Character, Bite on and the speaker sim bypassed is the stress case.
def alias_spectrum(binary, f0, cab):
    y = render(
        sine(f0, 3, -12), binary=binary, Drive=100, Character=100, Bite=100, **{"Cab Bypass": cab}
    )
    spec = np.abs(np.fft.rfft(y[-SR:] * np.hanning(SR)))
    spec /= spec[f0]
    harm = np.zeros(len(spec), bool)
    for k in range(1, int((SR / 2) // f0) + 1):
        harm[max(k * f0 - 3, 0) : k * f0 + 4] = True
    harm[:20] = True  # ignore DC and the window skirt
    return spec, db(np.max(np.where(harm, 0.0, spec)))


ax = axes[2]
results = {}
for name, binary in (("1x", RENDER_1X), ("4x", RENDER)):
    if not os.path.exists(binary):
        print(f"  (skipping {name}: {binary} not built)")
        continue
    for cab in (0, 1):
        for f0 in (441, 1100):
            spec, worst = alias_spectrum(binary, f0, cab)
            results[(name, cab, f0)] = worst
            print(f"  {name} cab bypass {cab} {f0:5d} Hz: worst alias {worst:6.1f} dBc")
            if f0 == 1100 and cab == 1:
                ax.plot(np.arange(len(spec)), db(spec), lw=0.7, label=f"{name}, Cab Bypass")
ax.set_title("1100 Hz, Drive and Character 100%: aliases")
ax.set_xlabel("frequency (Hz)")
ax.set_ylabel("dB relative to fundamental")
ax.set_ylim(-140, 5)
ax.set_xlim(0, SR / 2)
ax.grid(True, alpha=0.3)
ax.legend()

if len({k[0] for k in results}) == 2:
    for cab in (0, 1):
        for f0 in (441, 1100):
            gain = results[("1x", cab, f0)] - results[("4x", cab, f0)]
            check(
                gain >= 15, f"cab bypass {cab}, {f0} Hz: 4x lowers the worst alias by {gain:.1f} dB"
            )
    w = results[("4x", 0, 441)]
    check(w < -60, f"voiced, 441 Hz: worst alias with 4x {w:.1f} dBc (< -60 dBc)")
save_plot(fig, "harmonics")
write_csv("harmonics", ("f0_hz", "drive", "character", "harmonic", "level_dbc"), harm_rows)
write_csv(
    "aliasing",
    ("build", "cab_bypass", "f0_hz", "worst_alias_dbc"),
    ((name, cab, f0, worst) for (name, cab, f0), worst in results.items()),
)
finish()
