# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Realistic playing scenarios, rendered for A/B listening and checked by measurement.

Each scenario runs a bass-like phrase through the effect at a plausible setting
and writes, to tests/out/basspreamp/scenarios/:

  <scenario>_dry.wav       the input
  <scenario>_wet.wav       the effect output, as it comes
  <scenario>_matched.wav   the output gain-matched (RMS) to the input, for fair A/B
  <scenario>_ab.wav        dry, matched, dry, matched with a short gap between

By default the phrases are synthesised (additive plucked-string model with a pick
transient: deterministic, exact pitch, no licensing issue). To use a real clean DI
recording instead, put it at tests/data/bass-di.flac (or .wav), or point the
BASS_DI environment variable at any file ffmpeg can read. The recording replaces
every phrase, and output goes to scenarios-<file name>/.

The checks are sanity limits (no overs, no hang or DC after the notes stop, the
clean setting stays transparent, more Drive means more squash). The energy-above-300-Hz
figure is reported but not checked: the traced speaker voicing makes the preamp path darker.
Whether it sounds good is for a human to judge from the WAVs.
"""

import os
import subprocess

import numpy as np

from fxtest import OUT, ROOT, SR, check, db, finish, plt, render, save_plot, write_csv, write_wav

print("test_scenarios")

# --- Source material -------------------------------------------------------

NOTE = {"B0": 30.87, "E1": 41.20, "G1": 49.00, "A1": 55.00, "B1": 61.74, "D2": 73.42, "E2": 82.41}
BPM = 100
EIGHTH = 60 / BPM / 2


def pluck(f0, dur, vel=0.7, bright=1.2, tau=0.9, pick=0.15, rng=None):
    """One plucked-string note: partials with slow-decaying lows and quickly
    fading highs, slight stiffness inharmonicity, and a short pick-noise burst."""
    t = np.arange(int(dur * SR)) / SR
    y = np.zeros_like(t)
    for k in range(1, 40):
        fk = k * f0 * np.sqrt(1 + 1e-4 * k * k)
        if fk > 9000:
            break
        amp = k ** (-bright) * abs(np.sin(np.pi * k * 0.18)) + 0.02 / k
        y += amp * np.exp(-t * (1 + 0.5 * (k - 1)) / tau) * np.sin(2 * np.pi * fk * t)
    y *= np.minimum(t / 0.004, 1)  # 4 ms attack
    noise = rng.standard_normal(len(t)) * np.exp(-t / 0.008)
    lp = np.zeros_like(noise)  # one-pole low-pass at about 3 kHz
    a = np.exp(-2 * np.pi * 3000 / SR)
    for i in range(1, len(noise)):
        lp[i] = (1 - a) * noise[i] + a * lp[i - 1]
    y = y / np.max(np.abs(y)) + pick * vel * lp / np.max(np.abs(lp))
    return vel * y


def phrase(notes, rng, **kw):
    """notes: (name, eighths-long, velocity); notes ring into the next one."""
    out = np.zeros(int((sum(n[1] for n in notes) * EIGHTH + 1.5) * SR))
    pos = 0
    for name, eighths, vel in notes:
        y = pluck(NOTE[name], eighths * EIGHTH + 0.5, vel, rng=rng, **kw)
        out[pos : pos + len(y)] += y[: len(out) - pos]
        pos += int(eighths * EIGHTH * SR)
    return out


def normalise(x, peak_db):
    """Scale x so its peak sits at peak_db dBFS, then add 1 s of silence."""
    x = x * 10 ** (peak_db / 20) / np.max(np.abs(x))
    return np.concatenate([x, np.zeros(SR)])


def load_di(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True,
        check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)[: 20 * SR]


def sources():
    di = os.environ.get("BASS_DI")
    if not di:
        for ext in ("flac", "wav"):
            cand = os.path.join(ROOT, "tests", "data", f"bass-di.{ext}")
            if os.path.exists(cand):
                di = cand
                break
    if di:
        y = load_di(di)
        print(f"  using recording {di}")
        tag = os.path.splitext(os.path.basename(di))[0]
        return {k: y for k in ("groove", "lowB", "slap")}, f"scenarios-{tag}"
    rng = np.random.default_rng(1)
    groove = [(n, e, v) for n, e, v in (
        ("E1", 2, 0.8), ("E1", 1, 0.5), ("G1", 1, 0.6), ("A1", 2, 0.8), ("A1", 1, 0.5),
        ("B1", 1, 0.6), ("D2", 2, 0.8), ("B1", 1, 0.5), ("A1", 1, 0.6), ("G1", 2, 0.7),
        ("E1", 4, 0.9),
    )]  # fmt: skip
    low_b = [("B0", 4, 0.8), ("B0", 2, 0.6), ("E1", 2, 0.7), ("B0", 6, 0.9)]
    slap = [("E1", 1, 1.0), ("E2", 1, 1.0), ("E1", 1, 0.9), ("E2", 1, 1.0),
            ("G1", 1, 1.0), ("D2", 1, 0.9), ("A1", 1, 1.0), ("E2", 1, 1.0)]  # fmt: skip
    return {
        "groove": phrase(groove, rng),
        "lowB": phrase(low_b, rng, tau=1.4),
        "slap": phrase(slap, rng, bright=0.6, pick=0.5, tau=0.35),
    }, "scenarios"


# --- Scenarios -------------------------------------------------------------
# (name, source, input peak dBFS, effect settings). The settings are plausible
# starting points chosen for this test, not measured from any hardware.

SCENARIOS = [
    ("clean_di", "groove", -12, dict(Blend=0, Drive=0)),
    ("warm", "groove", -12, dict(Blend=50, Drive=30, Presence=30)),
    ("grit", "groove", -12, dict(Blend=70, Drive=60, Presence=50)),
    ("heavy", "groove", -12, dict(Blend=100, Drive=100, Presence=70)),
    ("blend_cancel", "slap", -12, dict(Blend=50, Drive=100, Presence=50)),
    ("hot_input", "groove", -1, dict(Blend=100, Drive=100, Presence=70, Level=12)),
    ("low_b", "lowB", -12, dict(Blend=100, Drive=60, Bass=6, **{"Bass Shift": 1})),
    ("slap_bright", "slap", -12, dict(Blend=60, Drive=40, Presence=60, Treble=4)),
    ("eq_max", "groove", -12, dict(Blend=60, Drive=40, Bass=12, Mid=12, Treble=12)),
    ("eq_min", "groove", -12, dict(Blend=60, Drive=40, Bass=-12, Mid=-12, Treble=-12)),
]

BANDS = 1000 * 2.0 ** (np.arange(-31, 14) / 6)  # 1/6-octave centres, ~31 Hz to ~5 kHz


def rms(x):
    return float(np.sqrt(np.mean(x**2)))


def band_levels(x):
    """Long-term average spectrum in 1/6-octave bands (dB re full scale)."""
    nfft = 8192
    win = np.hanning(nfft)
    p = np.zeros(nfft // 2 + 1)
    for i in range(0, len(x) - nfft, nfft // 2):
        p += np.abs(np.fft.rfft(win * x[i : i + nfft])) ** 2
    f = np.fft.rfftfreq(nfft, 1 / SR)
    lo, hi = BANDS * 2 ** (-1 / 12), BANDS * 2 ** (1 / 12)
    return np.array(
        [
            10 * np.log10(max(p[(f >= a) & (f < b)].sum(), 1e-30))
            for a, b in zip(lo, hi, strict=True)
        ]
    )


def centroid(x):
    s = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return float(np.sum(f * s) / np.sum(s))


def hf_fraction(x):
    """Fraction of energy above 300 Hz (harmonic 7 of the low E and up)."""
    s = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return float(s[f > 300].sum() / s.sum())


srcs, subdir = sources()
outdir = os.path.join(OUT, subdir)
os.makedirs(outdir, exist_ok=True)
gap = np.zeros(int(0.6 * SR))

metrics, spectra = {}, []
cols = 2
fig, axes = plt.subplots(
    (len(SCENARIOS) + 1) // cols, cols, figsize=(14, 3 * ((len(SCENARIOS) + 1) // cols)),
    constrained_layout=True, sharex=True,
)  # fmt: skip
for ax, (name, src, peak_db, params) in zip(axes.flat, SCENARIOS, strict=False):
    dry = normalise(srcs[src], peak_db)
    wet = render(dry, **params)
    active = slice(0, len(dry) - SR)  # exclude the silent tail
    g = rms(dry[active]) / rms(wet[active])
    matched = wet * g
    # The A/B clip is limited to the first 7 s so each file stays quick to audition.
    n = min(len(dry) - SR, 7 * SR)
    ab = np.concatenate([dry[:n], gap, matched[:n], gap, dry[:n], gap, matched[:n]])
    # Gain-matching can push peaks over 0 dBFS; scale the audition files together if so.
    safe = min(1.0, 0.98 / max(np.max(np.abs(matched)), np.max(np.abs(ab))))
    write_wav(f"{outdir}/{name}_dry.wav", dry)
    write_wav(f"{outdir}/{name}_wet.wav", wet)
    write_wav(f"{outdir}/{name}_matched.wav", matched * safe)
    write_wav(f"{outdir}/{name}_ab.wav", ab * safe)

    tail = wet[-SR // 2 :]
    m = dict(
        in_peak=float(db(np.max(np.abs(dry)))),
        out_peak=float(db(np.max(np.abs(wet)))),
        in_rms=float(db(rms(dry[active]))),
        out_rms=float(db(rms(wet[active]))),
        match_gain=float(db(g)),
        in_crest=float(db(np.max(np.abs(dry)) / rms(dry[active]))),
        out_crest=float(db(np.max(np.abs(matched)) / rms(matched[active]))),
        in_centroid=centroid(dry[active]),
        out_centroid=centroid(matched[active]),
        in_hf=hf_fraction(dry[active]),
        out_hf=hf_fraction(matched[active]),
        tail_rms=float(db(rms(tail))),
        tail_dc=float(db(abs(np.mean(tail)))),
    )
    metrics[name] = m
    print(
        f"  {name:13s} peak {m['out_peak']:6.2f} dBFS  match {m['match_gain']:+6.1f} dB  "
        f"crest {m['in_crest']:4.1f} -> {m['out_crest']:4.1f} dB  "
        f"centroid {m['in_centroid']:5.0f} -> {m['out_centroid']:5.0f} Hz  "
        f"HF>300 {100 * m['in_hf']:4.1f} -> {100 * m['out_hf']:4.1f} %  tail {m['tail_rms']:6.1f} dBFS"
    )
    check(np.all(np.isfinite(wet)), f"{name}: output is finite")
    check(m["out_peak"] <= 0.0, f"{name}: peak {m['out_peak']:.2f} dBFS <= 0 dBFS")
    check(
        m["tail_rms"] < -90, f"{name}: silent after the notes stop ({m['tail_rms']:.1f} dBFS < -90)"
    )

    for label, x in (("dry", dry[active]), ("wet_matched", matched[active])):
        lv = band_levels(x)
        spectra += [(name, label, float(fc), float(v)) for fc, v in zip(BANDS, lv, strict=True)]
        ax.semilogx(BANDS, lv, label=label)
    ax.set_title(f"{name}: {', '.join(f'{k}={v}' for k, v in params.items())}", fontsize=9)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8)
for ax in axes[-1]:
    ax.set_xlabel("frequency (Hz)")
for ax in axes[:, 0]:
    ax.set_ylabel("band level (dB)")
save_plot(fig, "scenarios_spectra")
write_csv("scenarios_spectra", ["scenario", "signal", "band_centre_hz", "level_db"], spectra)
write_csv(
    "scenarios_metrics",
    ["scenario", "metric", "value"],
    [(s, k, v) for s, m in metrics.items() for k, v in m.items()],
)
print(f"  wrote WAVs to {outdir}")

# --- Cross-scenario checks -------------------------------------------------
c = metrics["clean_di"]
check(
    abs(c["match_gain"]) < 1.0,
    f"clean_di is level-transparent ({c['match_gain']:+.2f} dB, |x| < 1)",
)
check(
    abs(c["out_centroid"] / c["in_centroid"] - 1) < 0.05,
    f"clean_di keeps the tone: centroid {c['in_centroid']:.0f} -> {c['out_centroid']:.0f} Hz (within 5 %)",
)
ladder = ("clean_di", "warm", "grit", "heavy")
crest = [metrics[s]["out_crest"] for s in ladder]
check(all(a >= b - 0.5 for a, b in zip(crest, crest[1:], strict=False)),
      "more Drive does not raise the crest factor (0.5 dB tolerance): " + " >= ".join(f"{v:.1f}" for v in crest))  # fmt: skip
check(
    crest[0] - crest[-1] >= 2,
    f"heavy squashes the dynamics: crest {crest[0]:.1f} -> {crest[-1]:.1f} dB (>= 2 dB less)",
)
finish()
