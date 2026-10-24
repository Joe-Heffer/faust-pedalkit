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
| `asymTanh(pos, neg)` | Asymmetric tanh clipper, which generates even-order harmonics |
| `softSat(v)` | Symmetric tanh saturation at ±v |
| `kneeClip(a, n)` | Clipper with adjustable hardness n, limiting at ±a |
| `asymSoftHard(pos, neg, n)` | Soft tanh above zero, a harder knee below; even harmonics grow with drive |
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

## Output safety

### `safety(lim)`

```faust
safety(lim, x) = ba.if(abs(x) <= t, x,
                       ma.signum(x) * (t + (lim - t) * ma.tanh((abs(x) - t) / (lim - t))))
with { t = 0.9 * lim; };
```

Transparent below 90 % of the ceiling `lim`, then a tanh knee that approaches `lim` and never exceeds it. Every effect ends with `pk.safety(0.989)`, about −0.1 dBFS, so no sample can pass 0 dBFS. It runs at the base rate, so driving it hard can alias.
