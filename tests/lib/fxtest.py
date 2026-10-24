"""Shared helpers for the offline effect tests.

The effect under test is named by the FX environment variable (set by
tests/run.sh). Signals are rendered by its compiled harness, build/<FX>/render,
which reads and writes raw mono float32. Sliders keep their declared defaults
unless a test overrides them by label. Only numpy and matplotlib are needed.
"""

import os
import subprocess
import sys

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SR = 48000
FX = os.environ.get("FX", "bassdrive")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDER = os.path.join(ROOT, "build", FX, "render")
RENDER_1X = os.path.join(ROOT, "build", FX, "render_1x")
OUT = os.path.join(ROOT, "tests", "out", FX)
os.makedirs(OUT, exist_ok=True)

_failures = []


def render(x, binary=RENDER, **params):
    """Process signal x through the effect, overriding sliders by label."""
    args = [binary, str(SR)] + [f"{k}={v}" for k, v in params.items()]
    res = subprocess.run(args, input=np.asarray(x, dtype=np.float32).tobytes(),
                         capture_output=True, check=True)
    return np.frombuffer(res.stdout, dtype=np.float32).astype(np.float64)


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
        X = np.fft.rfft(win * x[i:i + nfft])
        Y = np.fft.rfft(win * y[i:i + nfft])
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
    return np.array([spec[int(f0 * k)] if f0 * k < SR / 2 else 0.0
                     for k in range(1, n + 1)])


def write_wav(path, y):
    """Write y as 24-bit mono WAV for listening."""
    import wave
    pcm = (np.clip(y, -1, 1) * (2 ** 23 - 1)).astype("<i4")
    raw = b"".join(int(v).to_bytes(4, "little", signed=True)[:3] for v in pcm)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(3)
        w.setframerate(SR)
        w.writeframes(raw)


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
