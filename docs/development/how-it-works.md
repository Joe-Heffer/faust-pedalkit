# How it works

This page explains the ideas behind the repository for someone who has not written DSP or Faust before: what an effect is in code, how Faust describes it, and how one `.dsp` file becomes three plugins and a set of measurements. When you are ready to write an effect, continue with [Adding an effect](adding-an-effect.md).

## What DSP is

DSP means digital signal processing. Audio on a computer is a stream of numbers called samples. Each sample is the signal level at one instant, and a typical rate is 48,000 samples per second. An effect takes that stream in, does arithmetic on it and produces a new stream.

Most guitar and bass effects are built from a few operations:

* **Gain:** multiply each sample by a constant. A volume control does this.
* **Delay:** output the sample from N steps ago. Echo, chorus and reverb are made from delays.
* **Filtering:** mix the current sample with a few earlier inputs and outputs. This boosts or cuts ranges of frequency, as in a tone control or a wah.
* **Nonlinear shaping:** pass each sample through a curve such as `tanh`. This flattens peaks and adds harmonics, which is what distortion is.
* **Modulation:** vary a parameter over time with a slow oscillator, as in tremolo, chorus and phasers.

Two problems come up in almost every effect in this repository.

**Aliasing.** A nonlinear curve creates harmonics. Any harmonic above half the sample rate (the Nyquist frequency) cannot be represented and folds back down as an inharmonic tone that was never in the input. The remedy is oversampling: run the nonlinearity at four times the rate, filter, then return to the original rate. `pk.oversample4` does this in [the shared library](pedalkit-lib.md).

**Latency.** The oversampling filters delay the signal by a fixed number of samples (`pk.os4Latency`, 32 at the base rate). A dry path that is mixed back with a processed path must be delayed by the same amount, or the blend comb-filters. The plugin also reports the delay to the host, so the host can line tracks up.

## What Faust is

[Faust](https://faust.grame.fr/) is a functional language for describing DSP. You write the signal flow as a block diagram in text. The compiler turns it into efficient code, and the same `.dsp` file can target many plugin formats.

A program defines `process`, a block with some number of input and output signals. You wire blocks together with operators:

| Operator | Meaning |
|---|---|
| `a : b` | Series: the outputs of `a` feed the inputs of `b` |
| `a , b` | Parallel: side by side, not connected |
| `a <: b` | Split: fan the outputs of `a` out to the inputs of `b` |
| `a :> b` | Merge: sum the outputs of `a` into the inputs of `b` |
| `a ~ b` | Feedback: `b` feeds back into `a` through an implicit one-sample delay |
| `x @ n` | Delay `x` by `n` samples |

A small effect, a gain control followed by a soft clipper:

```faust
import("stdfaust.lib");

gain = hslider("Gain [unit:dB]", 0, -40, 20, 0.1) : ba.db2linear : si.smoo;

process = *(gain) : ma.tanh;
```

Read it left to right: multiply the input by a smoothed gain taken from a slider, then pass the result through `tanh`. A one-pole low-pass filter shows feedback:

```faust
a = 0.9;                      // closer to 1 means a lower cut-off
process = *(1 - a) : + ~ *(a);
```

The block `+ ~ *(a)` adds the input to the previous output scaled by `a`, so each output sample is `(1 - a) * x + a * y[n-1]`.

Points that matter when reading the effects here:

* **Controls are part of the signal graph.** `hslider` creates a plugin control and a signal you can use in the arithmetic. Its label, range and default become the plugin's parameter metadata, and tags such as `[unit:dB]` pass through to LV2, VST3 and CLAP.
* **`si.smoo` smooths a control** so that moving it does not cause clicks. Every control here is smoothed.
* **Everything is a signal.** A constant is a signal that never changes. That is why the compiler can optimise heavily, and why a pure waveshaper (a memoryless function) can be applied to four oversampled streams at once.
* **Libraries supply the building blocks.** `stdfaust.lib` brings in `fi.` (filters), `os.` (oscillators), `ba.` (basic helpers), `ma.` (maths) and more. This repository adds `pedalkit.lib`, imported as `pk`.

## From `.dsp` to plugins and measurements

```text
src/<name>.dsp
   |
   |-- faust2lv2 + tools/fix-ttl.py (+ tools/make-presets.py) --> build/<name>.lv2
   |-- faust + tools/vst3/faust-vst3.cpp + VST3 SDK ------------> build/<name>.vst3
   |-- faust + tools/clap/faust-clap.cpp + CLAP headers --------> build/<name>.clap
   `-- faust + tests/lib/render-arch.cpp -----------------------> build/<name>/render
                                                                     |
                                              tests/<name>/test_*.py renders signals,
                                              writes plots and CSV to tests/out/<name>/
```

1. **Compilation.** Faust flattens the block diagram into sample-by-sample equations and generates a C++ class. The class holds the state (delay memory, filter history) and a `compute` method that processes a block of samples.
2. **Architecture files.** An architecture wraps that class for one target. LV2 uses Faust's own template through `faust2lv2`. Faust has no VST3 script and its CLAP script hard-codes the plugin ID and reports no latency, so this repository supplies its own architectures for both (`tools/vst3/faust-vst3.cpp` and `tools/clap/faust-clap.cpp`). Each maps every control to a host parameter, numbered in UI order, and turns a bargraph tagged `[lv2:reportsLatency]` into the host's latency report. Neither has a GUI.
3. **Metadata.** The `declare` lines in the `.dsp` supply the name, version, licence, category and homepage. `tools/fix-ttl.py`, `tools/vst3-meta.py` and `tools/clap-meta.py` turn them into each format's metadata.
4. **Identity.** The LV2 URI is `urn:pedalkit/<name>`, the CLAP ID is `pedalkit.<name>` and the VST3 class ID is a UUID derived from `pedalkit.<name>`. Hosts store these in saved projects, so they never change after release. Parameters are stored by position, so new controls go at the end.
5. **Testing.** The tests use a fourth build of the same DSP, `build/<name>/render`, that reads raw float32 samples on stdin and writes them on stdout. A Python script feeds it test signals (sines, sweeps, silence), then measures what comes back. See [Tests and measurements](testing.md).
6. **Validation.** `lv2lint`, Steinberg's VST3 validator, pluginval and clap-validator check each format. CI runs them on every push (see [Linting and CI](ci.md)).
7. **Release.** Each effect is versioned and released on its own, built in a Debian 12 image so the plugins load on current Ubuntu and Debian (see [Releasing](releasing.md)).

## Why it is built this way

A Faust effect is a written-down graph with named constants. Each constant can carry a note saying whether it is documented, reported, inferred or chosen, and the offline tests can measure the result. Nobody can listen during automated development, so measurement stands in for the ear: harmonics, frequency response, aliasing and levels. Each effect page then lists the constants that a person should tune by listening.

## Where to go next

* [Designing new sounds](designing-new-sounds.md): the kinds of effect and how to write design notes.
* [Adding an effect](adding-an-effect.md): the step-by-step workflow.
* [Shared library](pedalkit-lib.md): the building blocks in `pedalkit.lib`.
* [BassDrive](../bassdrive/index.md): a worked example with controls, measurements and plots.
