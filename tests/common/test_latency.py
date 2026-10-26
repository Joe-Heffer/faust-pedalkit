# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""The latency the effect reports is the latency it has, and it stays small.

Hosts delay every other track by the reported latency, so the report must
match the plug-in's bulk delay: report too much and the effect plays early,
report too little and it plays late, and a dry path that skips the
oversampler's delay shows up as signal before the reported latency (the comb
filter AGENTS.md warns about). Players also feel the delay itself, so it has a
budget.

The impulse response is measured with quiet noise, so most effects are close
to linear, at the defaults and with every control at its minimum and at its
maximum. Two checks per setting:

* almost no energy arrives before the reported latency (over-reporting, or an
  unaligned dry path)
* the strongest tap lies at most PEAK_SLACK samples after it (under-reporting,
  for instance a second oversampler that the report leaves out)
"""

import numpy as np

from fxtest import SR, check, controls, finish, plt, render, reported_latency, save_plot, write_csv

print("test_latency")

# Chosen: 128 samples is 2.7 ms at 48 kHz, about the time sound takes to
# cross a metre of air. It leaves room for two 4x oversamplers (64) and an
# interface's own few milliseconds, and keeps the plug-in a small part of the
# round trip a player feels. An effect that needs more must raise it here, in
# a reviewed change, and say why in its notes.
LATENCY_BUDGET = 128

# Chosen: the effects' own filters put their strongest tap 0 to 11 samples
# after the reported latency (measured); a missing 4x oversampler would add 32.
PEAK_SLACK = 24

# Chosen: the oversampler's windowed-sinc pre-ringing puts at most 4e-5 of
# the energy before its centre (measured); an unaligned dry path puts far more.
EARLY_ENERGY = 1e-3

ctl = controls()
SETTINGS = {
    "defaults": {},
    "all minimum": {c["label"]: c["min"] for c in ctl},
    "all maximum": {c["label"]: c["max"] for c in ctl},
}

L = reported_latency()
print(f"  reported latency {L} samples ({1000 * L / SR:.2f} ms at {SR} Hz)")
check(
    0 <= L <= LATENCY_BUDGET, f"reported latency {L} samples within the budget of {LATENCY_BUDGET}"
)

rng = np.random.default_rng(3)
x = rng.normal(0, 10 ** (-40 / 20), 4 * SR)
nfft = 8192
lags = np.arange(L + 128)
rows = []
fig, ax = plt.subplots(figsize=(8, 4))
for name, params in SETTINGS.items():
    y = render(x, **params)
    # H1 estimate of the impulse response, from the cross-spectrum.
    win = np.hanning(nfft)
    sxy = np.zeros(nfft // 2 + 1, complex)
    sxx = np.zeros(nfft // 2 + 1)
    for i in range(0, len(x) - nfft, nfft // 2):
        X = np.fft.rfft(win * x[i : i + nfft])
        sxy += np.fft.rfft(win * y[i : i + nfft]) * np.conj(X)
        sxx += np.abs(X) ** 2
    h = np.fft.irfft(sxy / np.maximum(sxx, 1e-30), nfft)
    energy = h**2
    total = energy[: nfft // 2].sum()
    if total <= 0 or not np.isfinite(total):
        check(False, f"{name}: no measurable impulse response")
        continue
    early = energy[:L].sum() / total
    peak = int(np.argmax(np.abs(h[: nfft // 2])))
    check(
        early < EARLY_ENERGY,
        f"{name}: {100 * early:.4f} % of the energy arrives before {L} samples",
    )
    check(
        L <= peak <= L + PEAK_SLACK,
        f"{name}: strongest tap at {peak} samples ({peak - L:+d} from the report)",
    )
    hn = np.abs(h[lags]) / np.max(np.abs(h))
    rows += [(name, int(k), float(v)) for k, v in zip(lags, hn, strict=True)]
    ax.plot(lags, 20 * np.log10(np.maximum(hn, 1e-6)), label=name)

ax.axvline(L, color="k", ls="--", lw=1, label=f"reported latency ({L})")
ax.set(xlabel="lag (samples)", ylabel="|impulse response| (dB re peak)", ylim=(-80, 3))
ax.set_title("Impulse response against the reported latency (-40 dBFS noise)")
ax.grid(alpha=0.3)
ax.legend()
fig.tight_layout()
save_plot(fig, "latency")
write_csv("latency", ("setting", "lag_samples", "magnitude_re_peak"), rows)
write_csv(
    "latency_report",
    ("reported_samples", "budget_samples", "sample_rate_hz"),
    [(L, LATENCY_BUDGET, SR)],
)
finish()
