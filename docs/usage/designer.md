# Designing an effect in the browser

[Open the effect designer](../demo/designer/index.html){ .md-button .md-button--primary }

The designer is a web page where you build an effect from blocks and hear it straight away. You add blocks, wire them up, and press **Start**. The page writes the Faust code for you, compiles it in your browser and plays it through the same sources and levels as the [browser demo](browser.md). You never have to read the code, but it is one click away and can be downloaded as the starting point for a new `src/<name>.dsp`.

It is an early version (issue #95): the structure is in place, and some parts of the plan are still open issues.

## Using it

1. **Add** blocks from the row of buttons above the diagram. Each new block lands in the next free spot.
2. **Wire** them by dragging from a block's output (the dot on its right) to another block's input (the dot on its left). An input takes one wire, so a new wire replaces the old one. An output can feed any number of inputs, and a **Mix** block brings two paths back together. A wire that would make a feedback loop is refused. Drag a wire's input end off to remove it, or click the wire and press **Delete selected**.
3. **Set up** the selected block in the **Block** panel: its title, its type (for a Waveshaper or a Filter) and its parameters. Each parameter is either a fixed value or, with **Expose as a control** ticked, a control of the finished effect. Exposed controls appear in the **Controls** panel.
4. Press **Start** to listen, with the test riffs, an audio file or a live input, as in the demo.
5. **Code** shows the generated Faust, with **Copy** and **Download .dsp**. **Export** and **Import** save and load the design as JSON. The page also keeps your design in the browser between visits.

### Blocks

| Block | Faust | Parameters |
|---|---|---|
| Gain | `*(ba.db2linear(g))` | gain, −24 to +24 dB |
| Waveshaper | `pk.softSat`, `pk.asymTanh`, `pk.kneeClip` or `pk.asymSoftHard`, inside `pk.oversample4` | drive (0 to 40 dB) and the shaper's ceilings (−24 to 0 dB) and hardness (0 to 100 %) |
| Filter | `fi.lowpass` or `fi.highpass` (order 1 or 2), or a peaking EQ (`fi.peak_eq_cq`) | frequency (20 Hz to 20 kHz), and for the peaking EQ gain (±18 dB) and width (0.1 to 4 octaves) |
| DC blocker | `fi.dcblockerat(5)` | none |
| Mix | `a * (1 - m) + b * m` | balance, 0 % (A only) to 100 % (B only) |

The palette is one table in `web/designer/blocks.js`: each block's ports, parameters (unit, range, default, tooltip) and Faust template. Adding a block is a new entry there. Every range and default is chosen, to cover what is useful on a bass or guitar without leaving the range where each function behaves. The hardness range maps 0–100 % onto `pk.kneeClip`'s `n` from 1 to 10. Parameters are in dB, Hz, % or octaves, so every exposed control carries a unit.

## What the generated code does for you

The generator (`web/designer/generate.js`) applies the rules in AGENTS.md, so a design can't break them:

* **Named signals.** Each block becomes one line inside a `with` block, in processing order, such as `filter1 = waveshaper1 : fi.lowpass(2, filter1Freq);`. A fan-out is a name used twice. The code reads like a list of the diagram's blocks, and a comment at the top gives the signal flow.
* **Oversampling.** Each Waveshaper runs inside `pk.oversample4`, together with its drive gain, so the oversampled function stays memoryless. Filters always stay outside.
* **Latency compensation.** The generator tracks the latency of every path. Where two paths with different latencies meet at a Mix, the shorter one gets the matching `@(...)` delay, so a dry/wet blend doesn't comb-filter. The total is reported with the `Latency` bargraph, as in BassDrive. A design with more than 128 samples of latency (more than four waveshapers in series) gets a warning.
* **Controls.** A fixed value becomes a named constant marked `// chosen in the designer`. An exposed one becomes an `hslider` with a label, unit, range, default, tooltip and `si.smoo`, numbered in the order the controls appear. Frequencies use a log-scale slider.
* **Safety.** The output always ends with `pk.safety(0.989)`.
* **Metadata.** The `declare`s (name, description, author, `MIT`, `0.1.0`, an `lv2class` chosen from the blocks) and an SPDX header.

Blocks that don't reach the Output make no sound, so they are left out of the code. An unconnected Mix input gets silence, with a warning.

The downloaded `.dsp` passes the DSP part of the effect checklist (`tools/check-effects.py`) and builds as a plugin. To make it an effect in this repo, the rest of the checklist in AGENTS.md still applies: notes, tests, docs and presets.

## How it works

* **Compiling.** The page compiles in a Web Worker (`web/designer/compiler-worker.js`) with libfaust, the Faust compiler built to WebAssembly that comes with faustwasm. The worker loads it on the first compile: about 3.5 MB of WebAssembly and 2.3 MB of Faust libraries, plus `pedalkit.lib`. It sends back the compiled module, and the page plays it through the demo's audio host (`web/shared/host.js`).
* **When it recompiles.** A change to the wiring, a block's type or title, or a fixed value recompiles, 300 ms after the last change (a chosen delay). Moving an exposed control only sets that parameter on the running effect, with no recompile.
* **Compile time.** In Node on the development machine, a design with one waveshaper compiled in about 0.2 s and one with four in about 0.9 s. Chromium took about 0.25 s for one. With the 300 ms delay, a change is heard within about a second for a few waveshapers.
* **Click-free swaps.** The new effect fades in while the old one fades out, over about 10 ms, as Bypass does. Filter and delay state starts afresh with each compile, which can be heard as a brief change in a long tail.
* **Shared code.** The demo and the designer share `web/shared/`: the audio graph, sources, levels and bypass (`host.js`), the test riffs (`riffs.js`) and the controls built from `dsp-meta.json` (`controls.js`).

`make web` copies the page, `web/shared/`, `src/lib/pedalkit.lib` and libfaust into `build/web/`, and the docs workflow publishes the designer as `demo/designer/`.

### Licences

The page and the code it generates are MIT. libfaust and faustwasm are LGPL-2.1-or-later (the [Faust licence](https://github.com/grame-cncm/faust/blob/master-dev/COPYING.txt) and faustwasm's `COPYING.txt`), served unmodified with their licence text from the [faustwasm sources](https://github.com/grame-cncm/faustwasm). The Faust libraries the generated code imports (`stdfaust.lib`) are the same ones the native plugins use.

## Checks

`make web-test` also tests the designer:

* `tests/web/test_designer.mjs` (Node's test runner) generates the code for each example design in `tests/web/designer/*.json` and checks that it matches the committed `.dsp` next to it, so any change to the generator shows in review (`UPDATE_SNAPSHOTS=1` rewrites them). It then compiles each one with libfaust, as the page does, and checks that the effect reports the latency the generator computed, that silence in gives silence out (below −120 dBFS), and that the peak stays at or below 0 dBFS with every exposed control at its maximum, and at its minimum.
* For `drywet.json`, a waveshaper on one path blended 50/50 with the dry path, the response at −40 dBFS must be flat to within 1 dB from 50 Hz to 10 kHz (a chosen limit), which shows the latency compensation works. The same check on a copy with the compensating delay removed must fail.
* Each committed `.dsp` is compiled with the system Faust and passed through `tools/check-effects.py --dsp-only`.

## Limitations

* **One way.** The diagram makes the code. Editing the code does not change the diagram.
* **No feedback or modulation.** Loops are refused, and there are no delay, modulation or other stateful blocks beyond filters.
* **Mono.**
* **Download size.** The first compile downloads about 6 MB (less compressed), once per visit until the browser caches it.
* **Two compilers.** The page compiles with Faust 2.90.0 (in faustwasm) and the plugins with the system Faust. The generator only uses library functions that the existing effects already use, and `make web-test` compiles the examples with both.
* **Phone screens.** The diagram scrolls sideways on a narrow screen. Dragging works with touch, but small screens are not yet comfortable.
