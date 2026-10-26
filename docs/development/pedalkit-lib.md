# Shared library

`src/lib/pedalkit.lib` holds the DSP shared by every effect. Import it with:

```faust
pk = library("pedalkit.lib");
```

The Makefile copies `src/lib/*.lib` next to each `.dsp` before building and passes `-I src/lib` to the offline renderer, so a plain `library()` call works for every target.

| Function | Purpose |
|---|---|
| `oversample4(f)` | 4x polyphase oversampling around a memoryless `f` |
| `oversample1(f)` | Pass-through with the same interface, for A/B tests |
| `os4Latency` | 32: the base-rate delay of `oversample4` |
| `oversample4c(f)` / `oversample1c(f)` | As `oversample4`/`oversample1`, but `f(x, c)` also takes a base-rate control `c` (two inputs: audio, control) |
| `os4CtrlDelay` | 16: the delay applied to `c` so that it meets the audio sample it was computed from |
| `asymTanh(pos, neg)` | Asymmetric tanh clipper, which generates even-order harmonics |
| `softSat(v)` | Symmetric tanh saturation at ±v |
| `kneeClip(a, n)` | Clipper with adjustable hardness n, limiting at ±a |
| `asymSoftHard(pos, neg, n)` | Soft tanh above zero, a harder knee below; even harmonics grow with drive |
| `biased(f)` | Turns shaper `f` into `f(x, b)`, moved off centre by `b` with no DC step; `biased(f)(x, 0) = f(x)` |
| `biasShift(thr, maxShift, att, rel)` | Base-rate bias control: charges towards up to −`maxShift` when the input passes `thr`, with attack `att` and release `rel` in seconds |
| `tf2a(b2, b1, b0, a1, a0, w)` / `tf1a(b1, b0, a0, w)` | Analogue 2nd/1st-order section with coefficients in rad/s, bilinear-transformed with prewarp at `w` (held below Nyquist) |
| `safety(lim)` | Soft limiter, transparent below 90 % of `lim`, that never exceeds `lim` |

When you write something reusable, put it here rather than copying it into an effect, and add it to this table and to the one in `AGENTS.md`. Don't change an existing signature without updating every effect that uses it, then rerun `make test` across all effects.

## Oversampling

```faust
oversample4(f)
oversample1(f)
os4Latency
```

`oversample4` runs `f` at four times the sample rate, which pushes the aliases of a nonlinearity's harmonics far enough up that the decimation filter removes most of them.

It is polyphase: a single 129-tap Blackman-windowed sinc low-pass `h[k]`, designed at the 4x rate with its cut-off at 0.45 times the base sample rate (21.6 kHz at 48 kHz), serves as both the interpolator and the decimator. Each of the four phases runs at the base rate, so Faust needs no multirate support:

```text
interpolated phase p:  w_p[n] = 4 · Σ_j h[4j + p] · x[n − j]
decimated output:      z[n]   = Σ_q Σ_j h[4j − q] · y_q[n − j]
```

!!! warning "`f` must be memoryless"
    `f` is applied separately to each of the four phase streams. That is only valid if `f` has no memory: a waveshaper such as `tanh`, not a filter. Keep filters outside the oversampler.

The end-to-end delay is `os4Latency` = 32 base-rate samples. Because it is a whole number, a parallel dry path can be aligned exactly with `@(pk.os4Latency)`.

`oversample1(f) = f` has the same interface, without the oversampling and without the delay. The test build `render_1x` swaps every `oversample4(` for `oversample1(` to measure what the oversampling buys.

### Oversampling with a control: `oversample4c(f)`

```faust
oversample4c(f)
oversample1c(f)
os4CtrlDelay
```

Behaviour that depends on what was played a moment ago (a bias that shifts, a headroom that sags) needs memory, and `f` inside the oversampler can't have any. `oversample4c` splits the two. The memory lives in a base-rate path that computes a control `c`, and `f(x, c)` stays memoryless in `x`:

```faust
clip = pk.biased(pk.softSat(0.6));                      // f(x, b)
bias = pk.biasShift(0.6, 0.3, 0.015, 0.15);             // base rate, with memory
stage = _ <: _, bias : pk.oversample4c(clip);           // audio, control in
```

The block takes the audio on its first input and the control on its second. `c` is held for the four phases of each base-rate sample, which is valid only if it is smooth, well below the base Nyquist frequency: an envelope or a bias, not audio. The interpolator delays `x` by half of `os4Latency`, so `c` is delayed by `os4CtrlDelay` (16) to meet the sample it came from. The end-to-end delay is `os4Latency`, as for `oversample4`. `render_1x` swaps in `oversample1c(f) = f`.

## Waveshapers

All the waveshapers have slope 1 at zero, so they are transparent for small signals.

### `asymTanh(pos, neg)`

```faust
asymTanh(pos, neg, x) = ba.if(x > 0, pos * ma.tanh(x / pos), neg * ma.tanh(x / neg));
```

Soft tanh knees at +`pos` and −`neg`. Unequal knees generate even-order harmonics and a DC offset, so block the DC afterwards.

### `softSat(v)`

```faust
softSat(v, x) = v * ma.tanh(x / v);
```

Symmetric soft saturation at ±`v`, for example an op-amp running into its supply rails.

### `kneeClip(a, n)`

```faust
kneeClip(a, n, x) = x / pow(1 + pow(abs(x) / a, n), 1 / n);
```

Limits at ±`a` with an adjustable hardness `n`. Small `n` is soft (`n` = 2 is close to tanh), and large `n` approaches a hard clip. It stays almost linear until close to `a`.

### `asymSoftHard(pos, neg, n)`

```faust
asymSoftHard(pos, neg, n, x) = ba.if(x > 0, pos * ma.tanh(x / pos), kneeClip(neg, n, x));
```

Soft tanh clipping above zero (an LED, say) and a harder knee below zero (a transistor stage running out of headroom). At low levels it is almost symmetric. Once the negative side reaches `neg` it clips sooner and harder, so even harmonics rise with drive. BassDrive uses it with `pos` = 1.7, `neg` = 0.8 and `n` = 6.

## Dynamic state

[Designing for feel](designing-for-feel.md) explains what these are for. Each one is either a base-rate control with memory or a memoryless shaper that takes a control, for use with `oversample4c`.

### `biased(f)`

```faust
biased(f, x, b) = f(x + b) - f(b);
```

Moves the operating point of shaper `f` by `b`. The `f(b)` term keeps the output centred on zero, so a moving bias changes the shape of the clipping (and the balance of even and odd harmonics) without a DC step. With `b` = 0 it is `f` itself, up to float rounding.

### `biasShift(thr, maxShift, att, rel)`

```faust
biasShift(thr, maxShift, att, rel) = abs
    : \(e).(maxShift * ma.tanh(max(0, e - thr) / thr))
    : si.onePoleSwitching(att, rel) : *(-1);
```

The offset a coupling capacitor picks up when the stage after it conducts on loud peaks, and loses through its bias resistor afterwards. Each sample's excess over `thr` sets a target, which saturates at `maxShift`. The shift charges towards it with time constant `att` and discharges with `rel`, both in seconds. The smoothing comes after the saturation, so the shift builds up over `att` however hard the stage is driven. Below `thr` the output is exactly 0. MidHump's Bloom control uses it with `thr` = 0.6, `maxShift` = 0.3, `att` = 15 ms and `rel` = 150 ms.

## Analogue sections

### `tf2a(b2, b1, b0, a1, a0, w)` / `tf1a(b1, b0, a0, w)`

```faust
tfMaxW = 0.9 * ma.PI * ma.SR;

tf2a(b2, b1, b0, a1, a0, w) = fi.tf2s(b2, b1 / ws, b0 / (ws * ws), a1 / ws, a0 / (ws * ws), ws)
with { ws = min(w, tfMaxW); };
tf1a(b1, b0, a0, w) = fi.tf1s(b1, b0 / ws, a0 / ws, ws)
with { ws = min(w, tfMaxW); };
```

First- and second-order analogue sections, with the coefficients in rad/s as they come out of a circuit analysis:

- `tf2a`: H(s) = (b2 s² + b1 s + b0) / (s² + a1 s + a0)
- `tf1a`: H(s) = (b1 s + b0) / (s + a0)

They are discretised with the bilinear transform, prewarped so that the digital response matches the analogue one exactly at `w` (rad/s). Pick `w` near the section's pole frequency. `fi.tf2s` and `fi.tf1s` expect s normalised to `w`, and these wrappers do that scaling.

The prewarp frequency is held at or below `tfMaxW`, 90 % of Nyquist. The bilinear constant is 1 / tan(w / 2·SR), which goes infinite at Nyquist and negative above it, and a negative constant gives an unstable filter. BassPreamp's first post-drive Sallen-Key section (`postSK1`) prewarps at 36 172 rad/s (5.76 kHz), above Nyquist at 8 kHz and 11.025 kHz, and produced NaN there before the clamp. The coefficients are normalised by the clamped value, so H(s) is unchanged and only the frequency matched exactly moves. At 44.1 kHz and above, no section in the repository is clamped.

## Output safety

### `safety(lim)`

```faust
safety(lim, x) = ba.if(abs(x) <= t, x,
                       ma.signum(x) * (t + (lim - t) * ma.tanh((abs(x) - t) / (lim - t))))
with { t = 0.9 * lim; };
```

Transparent below 90 % of the ceiling `lim`, then a tanh knee that approaches `lim` and never exceeds it. Every effect ends with `pk.safety(0.989)`, about −0.1 dBFS, so no sample can pass 0 dBFS. It runs at the base rate, so driving it hard can alias.
