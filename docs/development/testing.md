# Tests and measurements

The tests render signals through the compiled DSP offline and check the results numerically. Nothing needs an audio device or a plugin host, so they run the same way on a laptop and in CI.

```sh
make test                 # every effect
make -j4 test             # every effect, four at a time
make test FX=bassdrive    # one effect
tests/run.sh bassdrive    # the same, once the renderers are built
```

With `-j`, each effect's tests run as a separate target (`test-<name>`), in parallel, and their output is printed one effect at a time. A failing effect doesn't stop the others. `test_cpu.py` is left out of that parallel pass (`tests/run.sh --no-cpu`) and runs afterwards for each effect in turn, with nothing else running, because it measures time.

Each script prints `[PASS]` or `[FAIL]` lines and exits non-zero if any check fails. The results go to `tests/out/<name>/`.

## The render harness

The tests don't use the LV2 bundle. They use a separate renderer, `build/<name>/render`, built from the effect's `.dsp` with the Faust architecture file `tests/lib/render-arch.cpp`:

```sh
build/bassdrive/render <samplerate> [options] [Label=value[@seconds] ...] < in.f32 > out.f32
```

- It reads mono raw float32 samples on stdin and writes the processed samples to stdout.
- Controls are set by their label, for example `Gain=80 Balance=100`. Any control not named keeps its declared default.
- `Label=value@seconds` changes a control that far into the input, at that exact sample, as host automation does. Repeat a label for a sequence of changes.
- Before reading any input it runs two seconds of silence through the DSP, so the parameter smoothers settle on their targets.
- `--block N` sets the block size (default 256). `--latency` prints the latency the effect reports to hosts. `--bench` times `compute()` on the input instead of writing audio, and `--ftz` sets the FPU's flush-to-zero first, as the VST3 and CLAP wrappers do.

`build/<name>/render_1x` is the same DSP with `oversample4(` replaced by `oversample1(` and `oversample4c(` by `oversample1c(`. Comparing the two shows what the oversampling buys.

## Python helpers

Each test script imports what it needs from `tests/lib/fxtest.py`. `tests/run.sh` sets `PYTHONPATH` and the `FX` environment variable, which names the effect under test. Only numpy and matplotlib are needed.

| Name | What it is |
|---|---|
| `SR` | Sample rate for all tests: 48000 |
| `RENDER`, `RENDER_1X` | Paths of the oversampled and 1x renderers |
| `OUT` | The output directory, `tests/out/<name>/` |
| `render(x, binary=RENDER, events=(), block=None, **params)` | Process signal `x`, overriding sliders by label: `render(x, Gain=100)`. `events` is a list of `(label, value, seconds)` automation points |
| `reported_latency()` | The latency in samples the effect reports to hosts |
| `bench(x, block=64, ftz=False, **params)` | Time the DSP on `x`; returns nanoseconds per sample and the real-time factor |
| `controls()` | The effect's controls in parameter order (label, type, init, min, max, step), from `faust -json` |
| `sine(freq, dur, amp_db=-12)` | A sine of `dur` seconds at `amp_db` dBFS peak |
| `log_sweep(f0, f1, dur, amp_db=-12)` | An exponential sine sweep, plus its instantaneous frequency |
| `transfer(x, y, nfft=16384)` | H1 transfer-function estimate (Welch-averaged cross-spectrum); returns `(f, H)` |
| `harmonics(y, f0, n=10)` | Amplitudes of harmonics 1 to `n` over the last whole second. `f0` must be a whole number of hertz. |
| `pluck(f0, dur, amp_db=-12, decay=0.5, n=8)` | A synthetic plucked note: harmonics 1 to `n` at 1/k amplitude, a 1 ms attack and an exponential decay. Use `n=1` to measure the harmonics an effect adds. |
| `burst(f0, levels_db, durs)` | A tone stepping through `levels_db`, `durs` seconds each, with continuous phase (quiet, loud, quiet, say) |
| `harmonics_over_time(y, f0, n=5, periods=4, hop=0.0025)` | Short-time DC and harmonics 1 to `n`; returns `(t, a)`, where `a[i, k]` is harmonic `k` (0 is DC) in the window centred at `t[i]` |
| `harmonic_trajectory(f0, levels_db, n=7, **params)` | Steady-state harmonics of a sine at each input level: the cleanup curve |
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

## Checks every effect gets

`tests/run.sh` runs the scripts in `tests/common/` for every effect after its own (`make test` runs `test_cpu.py` separately, see above), reading the controls from `build/<name>/controls.json`, so they need no per-effect code:

| Test | What it checks |
|---|---|
| `test_latency.py` | The reported latency is within budget and matches the measured impulse response |
| `test_zipper.py` | No control clicks when a host jumps it from one end of its range to the other |
| `test_cpu.py` | CPU per instance, and no subnormal slow-down once the input falls silent |
| `test_recovery.py` | After full-scale noise, the output decays to silence and stays finite |

[Playing feel, CPU and stability](feel-cpu-stability.md) explains the limits and what to do when one fails.

## What every effect must test

| Test | Why |
|---|---|
| Silence in gives silence out, at every extreme setting | Catches denormals, DC offsets, NaNs and self-oscillation |
| Peak ≤ 0 dBFS at the extreme settings, with square waves, noise, sweeps and impulses | Proves the safety limiter holds |
| Frequency response at several settings | Checks the filters and EQ against the circuit notes |
| Harmonic content | Checks the character of the nonlinearity against the reference measurements |
| Aliasing, `RENDER` against `RENDER_1X` (if the effect oversamples) | Shows what the oversampling buys |

Effects whose behaviour depends on time or playing level should also test it with the dynamic helpers: a cleanup curve, a quiet–loud–quiet burst and a pluck. [Designing for feel](designing-for-feel.md) covers which measurement shows which mechanism, and `tests/midhump/test_dynamics.py` is a worked example.

## Output formats

Results are written in open formats, so they can be reused without reading values off an image:

- **Plots:** SVG, via `save_plot`.
- **Data:** CSV, via `write_csv`, with one row per data point in long format. For example, `harmonics.csv` has the columns `f0_hz, gain, harmonic, level_dbc`.
- **Listening renders:** WAV, via `write_wav`. Any audio that gets committed must be FLAC, but test output is never committed.

The plots and CSV files are published on each effect's page on this site, and CI uploads the whole of `tests/out/` as the `test-output` artifact of each run.
