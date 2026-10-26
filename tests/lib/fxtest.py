# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Shared helpers for the offline effect tests.

The effect under test is named by the FX environment variable (set by
tests/run.sh). Signals are rendered by its compiled harness, build/<FX>/render,
which reads and writes raw mono float32. Sliders keep their declared defaults
unless a test overrides them by label. Only numpy and matplotlib are needed.

Results go to tests/out/<FX>/ in open formats: plots as SVG (save_plot), the
numbers behind them as CSV (write_csv) and audio as WAV (write_wav).
"""

import csv
import json
import os
import subprocess
import sys
import tomllib

import matplotlib
import numpy as np

matplotlib.use("Agg")
# Re-exported for the test scripts; must come after selecting the backend.
import matplotlib.pyplot as plt  # noqa: E402, F401

SR = 48000
FX = os.environ.get("FX", "bassdrive")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDER = os.path.join(ROOT, "build", FX, "render")
RENDER_1X = os.path.join(ROOT, "build", FX, "render_1x")
OUT = os.path.join(ROOT, "tests", "out", FX)
PRESETS = os.path.join(ROOT, "src", f"{FX}.presets.toml")
CONTROLS = os.path.join(ROOT, "build", FX, "controls.json")
os.makedirs(OUT, exist_ok=True)

_failures = []


def render(x, binary=RENDER, sr=SR, events=(), block=None, **params):
    """Process signal x at sample rate sr, overriding sliders by label.

    events is a sequence of (label, value, seconds): each control change is
    applied at that point of x, at its exact sample, as host automation is.
    block sets the processing block size (the harness default is 256).
    """
    args = [binary, str(sr)] + [f"{k}={v}" for k, v in params.items()]
    args += [f"{k}={v}@{t}" for k, v, t in events]
    if block:
        args += ["--block", str(block)]
    res = subprocess.run(
        args, input=np.asarray(x, dtype=np.float32).tobytes(), capture_output=True, check=True
    )
    return np.frombuffer(res.stdout, dtype=np.float32).astype(np.float64)


def reported_latency(binary=RENDER, sr=SR):
    """The latency in samples that the effect reports to hosts (0 if none)."""
    res = subprocess.run([binary, str(sr), "--latency"], capture_output=True, check=True)
    return int(res.stdout.decode().strip())


def bench(x, binary=RENDER, sr=SR, block=64, ftz=False, **params):
    """Time the DSP on x; returns (ns per sample, times faster than real time).

    The figure is for one instance on one core, best of five passes, and
    excludes process start-up and I/O. ftz flushes subnormals to zero, as the
    VST3 and CLAP wrappers do; without it the DSP runs as an LV2 host that
    leaves the FPU alone would run it.
    """
    args = [binary, str(sr), "--bench", "--block", str(block)]
    args += ["--ftz"] if ftz else []
    args += [f"{k}={v}" for k, v in params.items()]
    res = subprocess.run(
        args, input=np.asarray(x, dtype=np.float32).tobytes(), capture_output=True, check=True
    )
    ns, factor = res.stdout.decode().split()
    return float(ns), float(factor)


def controls():
    """The effect's input controls in parameter order, from faust -json.

    Each is a dict with label, type (hslider, vslider, nentry, checkbox or
    button), init, min, max and step; checkboxes and buttons run from 0 to 1.
    """

    def walk(items):
        for item in items:
            if "items" in item:
                yield from walk(item["items"])
            else:
                yield item

    with open(CONTROLS) as f:
        ui = json.load(f)["ui"]
    out = []
    for c in walk(ui):
        if c["type"] in ("hbargraph", "vbargraph"):
            continue
        out.append(
            dict(
                label=c["label"],
                type=c["type"],
                init=float(c.get("init", 0)),
                min=float(c.get("min", 0)),
                max=float(c.get("max", 1)),
                step=float(c.get("step", 1)),
            )
        )
    return out


def db(x, floor=1e-12):
    return 20 * np.log10(np.maximum(np.abs(x), floor))


def sine(freq, dur, amp_db=-12.0):
    t = np.arange(int(dur * SR)) / SR
    return 10 ** (amp_db / 20) * np.sin(2 * np.pi * freq * t)


def log_sweep(f0, f1, dur, amp_db=-12.0):
    """Exponential sine sweep; also returns the instantaneous frequency."""
    t = np.arange(int(dur * SR)) / SR
    k = np.log(f1 / f0)
    phase = 2 * np.pi * f0 * dur / k * (np.exp(t * k / dur) - 1)
    return 10 ** (amp_db / 20) * np.sin(phase), f0 * np.exp(t * k / dur)


def transfer(x, y, nfft=16384):
    """H1 transfer-function estimate (Welch-averaged cross-spectrum)."""
    win = np.hanning(nfft)
    hop = nfft // 2
    sxy = np.zeros(nfft // 2 + 1, complex)
    sxx = np.zeros(nfft // 2 + 1)
    for i in range(0, len(x) - nfft, hop):
        X = np.fft.rfft(win * x[i : i + nfft])
        Y = np.fft.rfft(win * y[i : i + nfft])
        sxy += Y * np.conj(X)
        sxx += np.abs(X) ** 2
    f = np.fft.rfftfreq(nfft, 1 / SR)
    return f, sxy / np.maximum(sxx, 1e-30)


def harmonics(y, f0, n=10):
    """Amplitudes of harmonics 1..n of f0 over the last whole second of y.

    f0 must be a whole number of hertz, so each harmonic sits exactly on a bin.
    """
    seg = y[-SR:]
    spec = np.abs(np.fft.rfft(seg)) * 2 / len(seg)
    return np.array([spec[int(f0 * k)] if f0 * k < SR / 2 else 0.0 for k in range(1, n + 1)])


def pluck(f0, dur, amp_db=-12.0, decay=0.5, n=8):
    """Synthetic plucked note: harmonics 1..n of f0 at 1/k amplitude, a 1 ms
    attack and an exponential decay with time constant `decay` seconds.
    Peak level is amp_db. A stand-in for a guitar DI, not a model of one."""
    t = np.arange(int(dur * SR)) / SR
    tone = sum(np.sin(2 * np.pi * f0 * k * t) / k for k in range(1, n + 1))
    env = np.minimum(t / 0.001, 1) * np.exp(-t / decay)
    x = tone * env
    return 10 ** (amp_db / 20) * x / np.max(np.abs(x))


def burst(f0, levels_db, durs):
    """Tone of f0 in consecutive segments, at levels_db for durs seconds each,
    with phase continuous across the steps (e.g. quiet, loud, quiet)."""
    amp = np.concatenate(
        [np.full(int(d * SR), 10 ** (lv / 20)) for lv, d in zip(levels_db, durs, strict=True)]
    )
    t = np.arange(len(amp)) / SR
    return amp * np.sin(2 * np.pi * f0 * t)


def harmonics_over_time(y, f0, n=5, periods=4, hop=0.0025):
    """Short-time DC and harmonic amplitudes of y.

    Returns (t, a): t are the window centres in seconds and a[i, k] is the
    amplitude of harmonic k of f0 in window i, with k = 0 the mean (DC). The
    window is Hann and `periods` periods of f0 long, which sets the time
    resolution. A whole number of periods (at least 2) puts each harmonic on
    a zero of the others' leakage, so a steady tone reads exactly.
    """
    m = int(round(periods * SR / f0))
    w = np.hanning(m)
    step = int(hop * SR)
    starts = np.arange(0, len(y) - m, step)
    tt = np.arange(m) / SR
    basis = np.array([np.exp(-2j * np.pi * f0 * k * tt) for k in range(n + 1)])
    a = np.empty((len(starts), n + 1))
    for i, s in enumerate(starts):
        seg = y[s : s + m] * w
        c = np.abs(basis @ seg) / w.sum()
        c[1:] *= 2
        a[i] = c
    return (starts + m / 2) / SR, a


def harmonic_trajectory(f0, levels_db, n=7, dur=1.5, binary=RENDER, **params):
    """Steady-state harmonics 1..n of a sine at each input level in levels_db.

    Returns an array of shape (len(levels_db), n): the cleanup curve, showing
    how the harmonic balance changes with playing strength. f0 must be a whole
    number of hertz (see harmonics)."""
    return np.array(
        [harmonics(render(sine(f0, dur, lv), binary=binary, **params), f0, n) for lv in levels_db]
    )


def loudness(y):
    """K-weighted mean square of y in dB (the ITU-R BS.1770 filter at 48 kHz,
    without gating). Good for comparing renders, not an absolute LUFS meter."""
    n = 2 * len(y)
    z = np.exp(2j * np.pi * np.fft.rfftfreq(n, 1 / SR) / SR)
    shelf = np.polyval([1.53512485958697, -2.69169618940638, 1.19839281085285], z) / np.polyval(
        [1, -1.69065929318241, 0.73248077421585], z
    )
    hp = np.polyval([1, -2, 1], z) / np.polyval([1, -1.99004745483398, 0.99007225036621], z)
    yk = np.fft.irfft(np.fft.rfft(y, n) * shelf * hp, n)[: len(y)]
    return 10 * np.log10(np.mean(yk**2) + 1e-30)


def presets():
    """Factory presets from src/<FX>.presets.toml as (name, controls) pairs,
    with controls keyed by label so they can be passed straight to render."""
    if not os.path.exists(PRESETS):
        return []
    with open(PRESETS, "rb") as f:
        return [(p["name"], p["controls"]) for p in tomllib.load(f).get("preset", [])]


def write_wav(path, y):
    """Write y as 24-bit mono WAV for listening."""
    import wave

    pcm = (np.clip(y, -1, 1) * (2**23 - 1)).astype("<i4")
    raw = b"".join(int(v).to_bytes(4, "little", signed=True)[:3] for v in pcm)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(3)
        w.setframerate(SR)
        w.writeframes(raw)


def save_plot(fig, name):
    """Save fig as OUT/<name>.svg."""
    path = os.path.join(OUT, f"{name}.svg")
    fig.savefig(path)
    print(f"  wrote {path}")


def write_csv(name, header, rows):
    """Write rows (an iterable of sequences) to OUT/<name>.csv under header."""
    path = os.path.join(OUT, f"{name}.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for row in rows:
            w.writerow([f"{v:.6g}" if isinstance(v, float) else v for v in row])
    print(f"  wrote {path}")


def check(cond, msg):
    tag = "PASS" if cond else "FAIL"
    print(f"  [{tag}] {msg}")
    if not cond:
        _failures.append(msg)


def finish():
    if _failures:
        print(f"{len(_failures)} check(s) failed")
        sys.exit(1)
    print("all checks passed")
