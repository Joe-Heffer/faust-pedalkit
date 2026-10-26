# Trying the effects in a browser

[Open the browser demo](../demo/index.html){ .md-button .md-button--primary }

The demo runs every effect in a web page, with nothing to install. It is the same Faust code as the LV2, VST3 and CLAP plugins, compiled to WebAssembly by [faustwasm](https://github.com/grame-cncm/faustwasm) and run in an [AudioWorklet](https://www.w3.org/TR/webaudio/#AudioWorklet), part of the W3C Web Audio standard. It works in current Firefox and Chromium-based browsers. A page address ending in `?fx=<name>`, such as `demo/index.html?fx=basspreamp`, opens with that effect selected.

To build an effect of your own from blocks, try the [effect designer](designer.md), which uses the same audio sources and levels.

## Using it

1. Choose an effect and a source:
    * **Test riff:** a short bass line synthesised in the page, so you hear something straight away. Choose a **Riff**: root and octave, a walking line, a disco octave pulse, slow sustained notes, a synth bass with a sub octave, or a staccato funk line. They are original patterns, with tempo, decay and sub level chosen to exercise different behaviour (attack transients, sustain, low-end tracking).
    * **Audio file:** any file your browser can decode, looped. A dry DI recording of a bass works best. The file stays on your computer.
    * **Microphone or audio interface:** live input. The browser asks for permission, and the page turns off echo cancellation, noise suppression and automatic gain so the effect gets the raw signal. Use headphones to avoid feedback.
2. Press **Start**. Browsers only allow audio after a click, so nothing plays until then.
3. Move the controls. They are built from the effect's own description (the same JSON as `make describe`), so they have the plugin's labels, units, ranges and defaults, and each one shows the plugin's tooltip text.
4. Tick **Bypass** to compare with the dry signal. The dry path is delayed by the latency the effect reports (32 samples for BassDrive, 64 for BassPreamp), so the comparison is time-aligned, and the switch crossfades over about 10 ms so it doesn't click.

**Input trim** sets the level into the effect, which matters for the drive effects: the test riff peaks at −10 dBFS, a typical level for a bass DI. **Output trim** and the peak meter are after the effect.

## How it is built

`make web` builds the demo into `build/web/`:

* `tools/web/package-lock.json` pins faustwasm (0.19.0, which bundles the Faust 2.90.0 compiler). `make web` installs it into `tools/web/node_modules/` with `npm ci`, so it needs Node.js and npm.
* faustwasm's `faust2wasm.js` compiles each `src/<name>.dsp`, with `src/lib/` on the include path, into `build/web/<name>/dsp-module.wasm` and its description `dsp-meta.json`.
* The page itself is `web/index.html`, `web/demo.js` and `web/demo.css`, with the audio host, riffs and controls in `web/shared/`, which the [effect designer](designer.md) shares. It loads faustwasm's runtime (`faustwasm/index.js`), not the compiler, so the browser downloads about 250 kB of script and 20–30 kB of WebAssembly per effect.

To try it locally, serve the folder over HTTP (AudioWorklet modules don't load from `file://`):

```sh
make web
python3 -m http.server -d build/web 8000   # then open http://localhost:8000/
```

Microphone input needs a secure context: `localhost` counts as one, and so does the published site, which is served over HTTPS.

The docs workflow runs `make web web-test` and publishes `build/web/` as `demo/` on this site.

## Checks

`make web-test` runs `tests/web/test_wasm.py`, which renders each effect's WebAssembly in Node with `tools/web/render.mjs` (through the same faustwasm runtime as the page, in 128-sample blocks as an AudioWorklet gets them) and checks that:

* silence in gives silence out (below −120 dBFS)
* the peak stays at or below 0 dBFS with every control at its maximum, and at its minimum, on a 0 dBFS input
* the output matches the native test renderer at the default, maximum and minimum settings, on a sine and a sweep, to within −60 dB of the native output's RMS level (a chosen threshold, far below anything audible, which still catches a wrong control mapping or a missing stage)
* each effect runs at least twice as fast as real time in Node (a chosen floor that catches a large slowdown)

The results are in `tests/out/web/wasm_vs_native.csv` and `tests/out/web/realtime.csv`. On the development container, with 4x oversampling, BassDrive ran at roughly 14–18 times real time and BassPreamp at roughly 7–10 times, so both have room to spare on a desktop.

## Limitations

* **Two compilers.** The plugins are built with the system Faust (2.88 in the toolchain image) and the demo with the Faust 2.90.0 inside faustwasm. Differences between their libraries would show up in `make web-test`.
* **Latency.** The browser adds its own audio buffering on top of the effect's latency. That is fine for listening to a file but can feel late for live playing; the plugins in a host with a small buffer are better for that.
* **Sample rate.** The effect runs at the rate the browser picks for your audio device (often 44.1 or 48 kHz). The tests and the plugins' measurements are at 48 kHz.
* **Slow devices.** The real-time check above is on a desktop processor. An old phone may not keep up with BassPreamp, which is the heavier of the two; the audio then breaks up. If the AudioWorklet can't be created at all, the page falls back to a ScriptProcessor node, which has more latency, and says so in its status line.
* **Firefox and Chromium.** The page has been driven automatically in Chromium. Check it by ear in Firefox, and in any browser you rely on.

## Web Audio Modules

[Web Audio Modules](https://github.com/webaudiomodules) (WAM) wrap an AudioWorklet effect so that WAM hosts, such as browser DAWs, can load it as a plugin. Issue #10 left open which WAM version Faust's generator targets. The generator is [faust2wam](https://github.com/webaudiomodules/faust2wam), published on npm as `@shren/faust2wam` (0.0.16 at the time of writing). It depends on `@webaudiomodules/api` 2.0.0-alpha and on faustwasm 0.15, so it targets WAM 2.0, and builds on an older faustwasm than the one pinned here.

The demo doesn't use WAM: a plain AudioWorklet node is all a single page needs, and it avoids a second, older copy of faustwasm. Publishing the effects as WAM 2.0 plugins could follow later from the same `.dsp` files.
