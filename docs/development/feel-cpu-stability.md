# Playing feel, CPU and stability

Players judge a plug-in on three things before they judge its tone:

* **Playing feel.** Guitarists and bassists notice delay and a dull response quickly. Oversampling should stop harshness without adding lag they can feel, and the plug-in must report its latency honestly, so the host can line it up with everything else.
* **CPU.** A player wants to run many instances in a session, or one live at a small buffer size, without glitches.
* **Stability.** Settings recall correctly, parameters don't zipper when automated, and nothing crashes the host.

This page sets out the rules for each, the budgets an effect has to meet, and which checks enforce them. Most of the checks run for every effect automatically, from `tests/common/`, so a new effect is held to them without writing a test.

## What is checked, and where

| Concern | Check | Limit | Runs in |
|---|---|---|---|
| Latency is small | `tests/common/test_latency.py` | reported latency ≤ 128 samples at 48 kHz | `make test` |
| Latency is reported honestly | `tests/common/test_latency.py` | < 0.1 % of the impulse response's energy below 16 kHz before the reported latency, strongest tap ≤ 24 samples after it | `make test` |
| The host compensates it | lv2lint, pluginval, clap-validator | latency port, `getLatencySamples()`, latency extension | `make lint pluginval clap-validate` |
| Low CPU per instance | `tests/common/test_cpu.py` | ≥ 20 times real time on noise, in 64-sample blocks | `make test` |
| No subnormal slow-down on silence | `tests/common/test_cpu.py` | a decaying tail costs ≤ 3 times live signal, without flush-to-zero | `make test` |
| No zipper or clicks | `tests/common/test_zipper.py` | a full-range jump of any control adds ≤ 6 dB over the steady state above 8 kHz | `make test` |
| Recovers after a hot input | `tests/common/test_recovery.py` | finite, and below −120 dBFS in the fourth second after the input stops | `make test` |
| Never clips the host | `tests/<name>/test_peak.py` | peak ≤ 0 dBFS at the extreme settings | `make test` |
| Works at every sample rate | `tests/<name>/test_samplerates.py` | finite, ≤ 0 dBFS and within 6 dB of 48 kHz, from 8 to 192 kHz | `make test` |
| Settings recall | `tools/check-params.py` (`params-stable` hook) | a released effect's controls keep their label, type and place | `make check` |
| Settings recall, presets, automation | Steinberg's validator, pluginval at strictness 10, clap-validator | state round trip, parameter fuzzing, varying block sizes and rates | `make vst3 pluginval clap clap-validate` |

The limits are chosen values, explained next to each constant in the test. Each test writes its numbers as CSV to `tests/out/<name>/` (`latency.csv`, `zipper.csv`, `cpu.csv`), and `latency.svg` and `zipper.svg` plot them. The effect pages publish them with the other measurements. If an effect needs a looser limit, change it in the test in a reviewed pull request and say why in the effect's design or circuit notes. Don't loosen it quietly.

## Playing feel and latency

### The budget

128 samples is 2.7 ms at 48 kHz, about the time sound takes to cross a metre of air. A player monitoring through an audio interface already has a few milliseconds of round trip, so this keeps the plug-in a small share of the delay they feel. Latency is fixed in samples, so it is shorter in milliseconds at higher sample rates.

| Source | Latency |
|---|---|
| One `pk.oversample4` | 32 samples (0.67 ms at 48 kHz) |
| Two in series, as in BassPreamp | 64 samples (1.33 ms) |
| A linear-phase FIR of N taps | (N − 1) / 2 samples |
| IIR filters, waveshapers, `si.smoo` | none reported; their group delay is part of the sound, as in the analogue circuit |

### Rules

* **Spend oversampling where it is heard.** Put every nonlinearity inside `pk.oversample4(f)`, so the harmonics it generates don't fold back as inharmonic fizz. The 4x rate is what lets an effect stay bright without aliasing: don't low-pass the output to hide aliasing instead, which is what makes a plug-in sound dull. The per-effect aliasing test (`RENDER` against `RENDER_1X`) shows what the oversampling buys.
* **One oversampler per run of nonlinearities.** Waveshapers that follow each other with no filter between them can share one call, `pk.oversample4(shapeA : shapeB)`, for one 32-sample delay instead of two. A filter between two stages forces two calls, because `f` must be memoryless. That is why BassPreamp has 64 samples.
* **Report the latency from the same constant that aligns the dry path.** BassPreamp defines `latencySamples = 2 * pk.os4Latency` once and uses it both for the clean path's delay and for the `Latency` bargraph, so the two cannot drift apart. Do the same when you add a stage.
* **Align every parallel path.** A dry, clean or side path that meets an oversampled path is delayed by the same amount, or the blend comb-filters and the attack smears. `test_latency.py` fails if more than 0.1 % of the energy below 16 kHz arrives before the reported latency, which is what an unaligned path looks like. It leaves out the top octave, where the oversampler's own linear-phase decimator rings symmetrically about its centre; an effect with nothing after the oversampler to darken it (BassGrit with Filter at 0) would otherwise show 1 to 5 % of its energy early with every path aligned.
* **No look-ahead without a reason in the notes.** A limiter or compressor with look-ahead, or a linear-phase EQ, adds its delay to the budget. It must be reported, and the notes must say why the player gains more than they lose.

### Checking it by ear

The tests measure the delay but not how it feels. When a change adds latency, play the effect through a small buffer (64 or 128 frames) against a dry track and listen for flamming or a softened attack.

## CPU

### Where the cost goes

The test machine measures each existing effect at 1.6 to 2.8 % of one core per instance at 48 kHz (`cpu.csv`). Most of that is:

* the oversampler: two 33-tap filters for each of four phases, 264 multiply-adds per base-rate sample, plus four evaluations of the waveshaper
* transcendental functions (`tanh`, `pow`, `exp`, `tan`) evaluated per sample
* filter coefficients recomputed per sample because they depend on a smoothed control

Cost scales with the sample rate: at 96 kHz an instance does twice the work per second.

### Rules

* **Measure before and after.** `bench(x, **params)` in `fxtest` times the DSP on any signal and returns nanoseconds per sample and the real-time factor. Quote the change in the pull request when it moves by more than about 10 %.
* **Keep transcendental functions few and inside the oversampler only when they shape the signal.** A gain law such as `ba.db2linear(level)` applied to a slider is computed once per block. The same law applied to a smoothed slider is computed every sample, which is the price of smooth automation. Accept that price for controls a player moves, but don't put it inside `pk.oversample4`, where it runs four times.
* **Never let state go subnormal.** When the input stops, filter states decay towards zero and pass through subnormal floats, and arithmetic on those is many times slower on most CPUs. An instance on a silent track can then cost more than one that is playing. The Makefile compiles every format with `FAUSTFLAGS = -ftz 1`, which flushes recursive state to zero below the smallest normal float, and the VST3 and CLAP wrappers also set the FPU's flush-to-zero during `process()`. LV2 hosts may leave it off, so the flag is what protects the LV2 build. `test_cpu.py` times a decaying tail without flush-to-zero and fails if it costs more than three times live signal. Without `-ftz 1` the existing effects measured 4.7 to 33 times.
* **Stay in single precision.** The plug-ins are built in 32-bit float. Don't compile with `-double` unless a measurement shows a filter needs it, and say so in the notes.

## Stability

### No zipper noise

Hosts apply automation, preset changes and MIDI-learnt knob moves as steps between blocks. Each control therefore ends in `: si.smoo`, a one-pole smoother with a 23 ms time constant at any sample rate.

* **Smooth switches too.** A `checkbox` that selects between two paths should crossfade them (BassPreamp's Cab Bypass) or glide a parameter (its Bass Shift and Mid Shift), rather than switching in one sample.
* **Smooth the value that reaches the signal.** If a control sets a filter frequency, smooth the control and compute the coefficients from it. A smoothed control that then passes through something with steps (`int`, `ba.if`, a lookup table) steps again, so smooth after that, or crossfade.
* `test_zipper.py` jumps every control from its minimum to its maximum and back under a 110 Hz sine, and looks for a burst above 8 kHz louder than the steady state on either side. With the smoothing removed from one control, the existing effects overshoot by 20 to 75 dB. With it, they stay within 5 dB.

### Settings that recall

Hosts save a plug-in's state by parameter position. The VST3 and CLAP wrappers number the controls in UI order (the `[n]` prefixes) and store their plain values in that order. LV2 stores them by port symbol, which includes the label. So, once an effect is released:

* **Don't rename, retype or reorder a control.** Add new controls at the end, with the next `[n]`. The `params-stable` pre-commit hook compares every effect with its latest release tag and fails on any change to an existing control.
* **Don't change what a control means.** Widening a range is safe. Narrowing it can clamp old values. Changing its unit or law (dB to %, linear to log) loads old projects at the wrong setting, so add a new control instead.
* **Don't rename the `.dsp`.** The plug-in IDs derive from it.
* **Presets set every control**, because LV2 hosts leave unlisted controls where they were.

Between them, Steinberg's validator, pluginval and clap-validator save and restore state, load presets and fuzz the parameters on every build.

### Nothing that can take the host down

Faust's generated `compute()` doesn't allocate, lock or make system calls, and it has no unbounded loops. Keep it that way:

* no `ffunction` that calls code which allocates, locks or does I/O
* no table, delay or `rdtable` whose size depends on a control
* every filter stable at every sample rate from 8 to 192 kHz: use `pk.tf2a` and `pk.tf1a`, which keep the prewarp frequency below Nyquist, and keep `test_samplerates.py` in the effect's tests
* every path through `pk.safety(0.989)`, so the output never passes 0 dBFS
* nothing that self-oscillates once driven hard: `test_recovery.py` drives each effect with full-scale noise at the defaults and at every control's minimum and maximum, then checks that it falls silent

A NaN or infinity in the input is not guarded against: it would stay in the filter state until the plug-in is reset. Hosts don't normally send one, and a guard would cost CPU on every sample, so this is a known limitation.

## Before you open a pull request

* `make test FX=<name>` passes, including the four checks in `tests/common/`, and you have read `latency.svg` and `zipper.svg`.
* The reported latency is fed from the same constant as the dry-path delay.
* `cpu.csv` is no more than about 10 % slower than on `main`, or the pull request says why.
* No released control was renamed, retyped or moved (`make check` runs the `params-stable` hook).
* `make vst3 pluginval clap clap-validate FX=<name>` passes.
* The pull request names what a player should check by ear: attack and flamming at a small buffer, and any control whose sweep sounds stepped.
