# Tests and measurements

The tests render signals through the compiled DSP offline and check the results numerically. Nothing needs an audio device or a plugin host, so they run the same way on a laptop and in CI.

```sh
make test                 # every effect
make test FX=bassdrive    # one effect
tests/run.sh bassdrive    # the same, once the renderers are built
```

Each script prints `[PASS]` or `[FAIL]` lines and exits non-zero if any check fails. The results go to `tests/out/<name>/`.

## The render harness

The tests don't use the LV2 bundle. They use a separate renderer, `build/<name>/render`, built from the effect's `.dsp` with the Faust architecture file `tests/lib/render-arch.cpp`:

```sh
build/bassdrive/render <samplerate> [Label=value ...] < in.f32 > out.f32
```

- It reads mono raw float32 samples on stdin and writes the processed samples to stdout.
- Controls are set by their label, for example `Gain=80 Balance=100`. Any control not named keeps its declared default.
- Before reading any input it runs two seconds of silence through the DSP, so the parameter smoothers settle on their targets.

`build/<name>/render_1x` is the same DSP with `oversample4(` replaced by `oversample1(`. Comparing the two shows what the oversampling buys.

## Python helpers

Each test script imports what it needs from `tests/lib/fxtest.py`. `tests/run.sh` sets `PYTHONPATH` and the `FX` environment variable, which names the effect under test. Only numpy and matplotlib are needed.

| Name | What it is |
|---|---|
| `SR` | Sample rate for all tests: 48000 |
| `RENDER`, `RENDER_1X` | Paths of the oversampled and 1x renderers |
| `OUT` | The output directory, `tests/out/<name>/` |
| `render(x, binary=RENDER, **params)` | Process signal `x`, overriding sliders by label: `render(x, Gain=100)` |
| `sine(freq, dur, amp_db=-12)` | A sine of `dur` seconds at `amp_db` dBFS peak |
| `log_sweep(f0, f1, dur, amp_db=-12)` | An exponential sine sweep, plus its instantaneous frequency |
| `transfer(x, y, nfft=16384)` | H1 transfer-function estimate (Welch-averaged cross-spectrum); returns `(f, H)` |
| `harmonics(y, f0, n=10)` | Amplitudes of harmonics 1 to `n` over the last whole second. `f0` must be a whole number of hertz. |
| `db(x)` | 20 log₁₀ \|x\|, floored at −240 dB |
| `save_plot(fig, name)` | Save a matplotlib figure as `OUT/<name>.svg` |
| `write_csv(name, header, rows)` | Save the data behind a plot as `OUT/<name>.csv` |
| `write_wav(path, y)` | Save a 24-bit mono WAV for listening |
| `check(cond, msg)` | Record a pass or fail |
| `finish()` | Print the summary and exit non-zero if any check failed |
| `plt` | `matplotlib.pyplot`, with the non-interactive Agg backend already selected |

A minimal test:

```python
"""Silence in must give silence out."""

import numpy as np

from fxtest import SR, check, finish, render

y = render(np.zeros(3 * SR), Gain=100, Level=12)
check(np.max(np.abs(y)) < 1e-6, "silence in gives silence out at full Gain")
finish()
```

## What every effect must test

| Test | Why |
|---|---|
| Silence in gives silence out, at every extreme setting | Catches denormals, DC offsets, NaNs and self-oscillation |
| Peak ≤ 0 dBFS at the extreme settings, with square waves, noise, sweeps and impulses | Proves the safety limiter holds |
| Frequency response at several settings | Checks the filters and EQ against the circuit notes |
| Harmonic content | Checks the character of the nonlinearity against the reference measurements |
| Aliasing, `RENDER` against `RENDER_1X` (if the effect oversamples) | Shows what the oversampling buys |

## Output formats

Results are written in open formats, so they can be reused without reading values off an image:

- **Plots:** SVG, via `save_plot`.
- **Data:** CSV, via `write_csv`, with one row per data point in long format. For example, `harmonics.csv` has the columns `f0_hz, gain, harmonic, level_dbc`.
- **Listening renders:** WAV, via `write_wav`. Any audio that gets committed must be FLAC, but test output is never committed.

The plots and CSV files are published on each effect's page on this site, and CI uploads the whole of `tests/out/` as the `test-output` artifact of each run.
