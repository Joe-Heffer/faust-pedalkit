# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Harmonic content at several Distortion settings, and the aliasing benefit of
4x oversampling compared with a 1x build of the same DSP."""

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

# Harmonic spectra for the open A string (55 Hz is too low to show the split
# at work, so use A at 110 Hz) and 220 Hz, both with the default Crossover.
for ax, f0 in zip(axes[:2], (110, 220), strict=True):
    width = 0.25
    for i, d in enumerate((25, 50, 100)):
        y = render(sine(f0, 3, -12), Distortion=d, Filter=30)
        hk = harmonics(y, f0, 10)
        rel = db(hk / hk[0])
        harm_rows.extend((f0, d, k, rel[k - 1]) for k in range(1, 11))
        ax.bar(
            np.arange(1, 11) + (i - 1) * width,
            rel + 120,
            width,
            bottom=-120,
            label=f"Distortion {d}%",
        )
        thd = np.sqrt(np.sum(hk[1:] ** 2)) / hk[0]
        even = np.sqrt(np.sum(hk[1::2] ** 2))
        odd = np.sqrt(np.sum(hk[2::2] ** 2))
        print(
            f"  {f0} Hz Distortion {d:3d}%: THD {100 * thd:5.1f}%  "
            f"H2 {rel[1]:6.1f} dBc  H3 {rel[2]:6.1f} dBc  "
            f"even/odd {db(even / max(odd, 1e-12)):+5.1f} dB"
        )
        if d == 100:
            ratio = db(even / max(odd, 1e-12))
            check(ratio < -30, f"{f0} Hz Distortion 100: even/odd {ratio:+.1f} dB (< -30, symmetric)")
    ax.set_title(f"Harmonics of {f0} Hz, -12 dBFS in, Filter 30%")
    ax.set_xlabel("harmonic number")
    ax.set_ylabel("level relative to fundamental (dB)")
    ax.set_xticks(range(1, 11))
    ax.set_ylim(-120, 5)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend()


# Aliasing. With f0 a whole number of hertz that does not divide 48 kHz, the
# true harmonics and the aliases land on different FFT bins. At full Distortion
# the clipper input is hundreds of times its threshold, so the output is close
# to a square wave and its harmonics fall only as 1/k. 4x oversampling cannot
# remove all aliasing from that. The checks are therefore on bass fundamentals
# (441 Hz is about the top of a four-string bass's fundamental range in
# practice); 1.1 kHz and 3.7 kHz are stress cases whose numbers are reported.
def alias_spectrum(binary, f0):
    y = render(sine(f0, 3, -12), binary=binary, Distortion=100, Filter=0)
    spec = np.abs(np.fft.rfft(y[-SR:] * np.hanning(SR)))
    spec /= spec[f0]
    harm = np.zeros(len(spec), bool)
    for k in range(1, int((SR / 2) // f0) + 1):
        harm[max(k * f0 - 3, 0) : k * f0 + 4] = True
    harm[:20] = True  # ignore DC and the window skirt
    return spec, db(np.max(np.where(harm, 0.0, spec)))


ax = axes[2]
results = {}
for name, binary in (("1x (reference)", RENDER_1X), ("4x oversampled", RENDER)):
    if not os.path.exists(binary):
        print(f"  (skipping {name}: {binary} not built)")
        continue
    for f0 in (3700, 1100, 441, 221):
        spec, worst = alias_spectrum(binary, f0)
        results[(name, f0)] = worst
        print(f"  {name:15s} {f0:5d} Hz: worst alias {worst:6.1f} dBc")
        if f0 == 441:
            ax.plot(np.arange(len(spec)), db(spec), lw=0.7, label=name)
ax.set_title("441 Hz at Distortion 100%, Filter 0%: harmonics and aliases")
ax.set_xlabel("frequency (Hz)")
ax.set_ylabel("dB relative to fundamental")
ax.set_ylim(-140, 5)
ax.set_xlim(0, SR / 2)
ax.grid(True, alpha=0.3)
ax.legend()

if ("1x (reference)", 441) in results and ("4x oversampled", 441) in results:
    for f0 in (441, 221):
        gain = results[("1x (reference)", f0)] - results[("4x oversampled", f0)]
        check(gain >= 20, f"{f0} Hz: 4x reduces worst alias by {gain:.1f} dB (>= 20 dB)")
    check(
        results[("4x oversampled", 441)] < -60,
        f"441 Hz: worst alias with 4x {results[('4x oversampled', 441)]:.1f} dBc (< -60 dBc)",
    )
    gain = results[("1x (reference)", 1100)] - results[("4x oversampled", 1100)]
    check(gain >= 12, f"1100 Hz stress case: 4x reduces worst alias by {gain:.1f} dB (>= 12 dB)")
save_plot(fig, "harmonics")
write_csv("harmonics", ("f0_hz", "distortion", "harmonic", "level_dbc"), harm_rows)
write_csv(
    "aliasing",
    ("build", "f0_hz", "worst_alias_dbc"),
    ((name, f0, worst) for (name, f0), worst in results.items()),
)
finish()
