// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// The audio side of the browser pages (the demo and the designer).
//
// Signal flow (all Web Audio nodes, mono):
//
//   source -> input trim -+-> effect A -> fade A -+-> wet -+-> output trim -> analyser -> speakers
//                         +-> effect B -> fade B -+        |
//                         +-> delay (effect latency) -> dry +
//
// The source is a synthesised test riff, a looping audio file or a live
// input. An effect is a faustwasm node made from a compiled factory; a new
// one fades in while the old one fades out (BYPASS_FADE_S), so switching
// effects, or recompiling in the designer, doesn't click. The dry path is
// delayed by the latency the effect reports, so Bypass switches between
// time-aligned signals.

import { FaustMonoDspGenerator } from "../faustwasm/index.js";
import { dbToGain } from "./controls.js";
import { makeRiff, RIFFS } from "./riffs.js";

// Chosen values (see docs/usage/browser.md).
export const BYPASS_FADE_S = 0.01; // crossfade time constant, avoids clicks
const RETIRE_MS = 100; // when a faded-out effect is destroyed: 10 time constants
const PEAK_FALL_DB_PER_S = 20; // peak meter release

export class Host {
    constructor() {
        this.ctx = null;
        this.graph = null;
        this.effect = null; // { node, fade, params: Set of its addresses }
        this.backend = "";
        this.values = {}; // control values by Faust address
        this.onOutputParam = () => {};
        this.sourceNode = null;
        this.micStream = null;
        this.riffBuffers = {};
        this.fileBuffer = null;
        this.running = false;
    }

    // Create the audio context and graph. Browsers allow audio only after a
    // user gesture, so call this from one.
    init({ inputDb = 0, outputDb = 0, bypass = false } = {}) {
        const ctx = new AudioContext({ latencyHint: "interactive" });
        const input = new GainNode(ctx, {
            gain: dbToGain(inputDb),
            channelCount: 1,
            channelCountMode: "explicit",
            channelInterpretation: "speakers",
        });
        const dryDelay = new DelayNode(ctx, { maxDelayTime: 0.1 });
        const dry = new GainNode(ctx, { gain: bypass ? 1 : 0 });
        const wet = new GainNode(ctx, { gain: bypass ? 0 : 1 });
        const output = new GainNode(ctx, { gain: dbToGain(outputDb) });
        const analyser = new AnalyserNode(ctx, { fftSize: 2048 });
        input.connect(dryDelay).connect(dry).connect(output);
        wet.connect(output);
        output.connect(analyser).connect(ctx.destination);
        this.ctx = ctx;
        this.graph = { input, dryDelay, dry, wet, output, analyser };
    }

    // Replace the running effect with one made from `factory` ({ module,
    // json, soundfiles }), carrying over the control values it shares with
    // the old one.
    async setEffect(factory, name) {
        const generator = new FaustMonoDspGenerator();
        let node = null;
        let backend = "AudioWorklet";
        try {
            node = await generator.createNode(this.ctx, name, factory, false);
        } catch (error) {
            console.warn("AudioWorklet node failed, falling back to ScriptProcessor", error);
        }
        if (!node) {
            node = await generator.createNode(this.ctx, name, factory, true, 512);
            backend = "ScriptProcessor (fallback)";
        }
        if (!node) throw new Error(`could not create the ${name} node`);
        const params = new Set(node.getParams());
        for (const [address, value] of Object.entries(this.values)) if (params.has(address)) node.setParamValue(address, value);
        node.setOutputParamHandler((address, value) => this.onOutputParam(address, value));

        const t = this.ctx.currentTime;
        const fade = new GainNode(this.ctx, { gain: 0 });
        this.graph.input.connect(node).connect(fade).connect(this.graph.wet);
        fade.gain.setTargetAtTime(1, t, BYPASS_FADE_S);
        const old = this.effect;
        this.effect = { node, fade, params };
        this.backend = backend;
        if (old) {
            old.node.setOutputParamHandler(() => {});
            old.fade.gain.setTargetAtTime(0, t, BYPASS_FADE_S);
            setTimeout(() => {
                this.graph.input.disconnect(old.node);
                old.node.disconnect();
                old.fade.disconnect();
                old.node.destroy();
            }, RETIRE_MS);
        }
    }

    setParam(address, value) {
        this.values[address] = value;
        if (this.effect?.params.has(address)) this.effect.node.setParamValue(address, value);
    }

    setLatency(samples) {
        if (this.graph) this.graph.dryDelay.delayTime.value = samples / this.ctx.sampleRate;
    }

    setBypass(on) {
        if (!this.graph) return;
        const t = this.ctx.currentTime;
        this.graph.dry.gain.setTargetAtTime(on ? 1 : 0, t, BYPASS_FADE_S);
        this.graph.wet.gain.setTargetAtTime(on ? 0 : 1, t, BYPASS_FADE_S);
    }

    setTrim(which, db) {
        if (this.graph) this.graph[which].gain.setTargetAtTime(dbToGain(db), this.ctx.currentTime, 0.01);
    }

    stopSource() {
        if (this.sourceNode) {
            if (this.sourceNode.stop) this.sourceNode.stop();
            this.sourceNode.disconnect();
            this.sourceNode = null;
        }
        if (this.micStream) {
            for (const track of this.micStream.getTracks()) track.stop();
            this.micStream = null;
        }
    }

    // kind is "riff" (with riff, a key of RIFFS), "file" (with file, a File)
    // or "mic" (with deviceId, "" for the default input).
    async startSource({ kind, riff, file, deviceId }) {
        this.stopSource();
        if (kind === "mic") {
            if (!navigator.mediaDevices?.getUserMedia) throw new Error("this browser offers no audio input here (it needs HTTPS)");
            this.micStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    deviceId: deviceId ? { exact: deviceId } : undefined,
                    echoCancellation: false,
                    noiseSuppression: false,
                    autoGainControl: false,
                },
            });
            this.sourceNode = new MediaStreamAudioSourceNode(this.ctx, { mediaStream: this.micStream });
        } else {
            let buffer;
            if (kind === "file") {
                if (!this.fileBuffer && file) this.fileBuffer = await this.ctx.decodeAudioData(await file.arrayBuffer());
                if (!this.fileBuffer) throw new Error("choose an audio file first");
                buffer = this.fileBuffer;
            } else {
                this.riffBuffers[riff] ??= makeRiff(this.ctx.sampleRate, RIFFS[riff]);
                buffer = this.riffBuffers[riff];
            }
            this.sourceNode = new AudioBufferSourceNode(this.ctx, { buffer, loop: true });
            this.sourceNode.start();
        }
        this.sourceNode.connect(this.graph.input);
    }

    // Linear peak of the last analyser block; 0 while stopped, because a
    // suspended context leaves its last block in the analyser.
    peak() {
        if (!this.graph || !this.running) return 0;
        const data = new Float32Array(this.graph.analyser.fftSize);
        this.graph.analyser.getFloatTimeDomainData(data);
        let peak = 0;
        for (const v of data) peak = Math.max(peak, Math.abs(v));
        return peak;
    }
}

// Wire the Setup and Levels panels that both pages share (the elements with
// the ids below) to `host`.
//   prepare()   called once, after the audio context exists and before the
//               first Start plays, to load the first effect
//   status(text, error)  shows a status line
//   onRunning() called whenever the running status should be redrawn
export function setupPanel(host, { prepare, status, onRunning }) {
    const $ = (id) => document.getElementById(id);
    const ui = {
        source: $("source"),
        riffRow: $("riff-row"),
        riff: $("riff"),
        fileRow: $("file-row"),
        file: $("file"),
        deviceRow: $("device-row"),
        device: $("device"),
        start: $("start"),
        bypass: $("bypass"),
        inputTrim: $("input-trim"),
        inputTrimValue: $("input-trim-value"),
        outputTrim: $("output-trim"),
        outputTrimValue: $("output-trim-value"),
        peak: $("peak"),
        peakValue: $("peak-value"),
    };

    const sourceSpec = () => ({ kind: ui.source.value, riff: ui.riff.value, file: ui.file.files[0], deviceId: ui.device.value });

    async function listDevices() {
        const devices = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "audioinput");
        const selected = ui.device.value;
        // Before permission is granted the browser may list no inputs, or
        // inputs without labels, so always offer the default input as well.
        ui.device.replaceChildren(
            new Option("Default input", "", false, !selected),
            ...devices
                .filter((d) => d.deviceId && d.deviceId !== "default")
                .map((d, i) => new Option(d.label || `Input ${i + 1}`, d.deviceId, false, d.deviceId === selected)),
        );
    }

    async function startSource() {
        await host.startSource(sourceSpec());
        if (ui.source.value === "mic") await listDevices();
    }

    async function start() {
        ui.start.disabled = true;
        try {
            if (!host.ctx) {
                status("Starting audio…");
                host.init({
                    inputDb: Number(ui.inputTrim.value),
                    outputDb: Number(ui.outputTrim.value),
                    bypass: ui.bypass.checked,
                });
                requestAnimationFrame(meterLoop);
                await prepare();
            }
            await host.ctx.resume();
            await startSource();
            host.running = true;
            ui.start.textContent = "Stop";
            onRunning();
        } catch (error) {
            console.error(error);
            status(`Could not start: ${error.message}`, true);
        } finally {
            ui.start.disabled = false;
        }
    }

    async function stop() {
        host.stopSource();
        host.running = false;
        ui.start.textContent = "Start";
        if (host.ctx) await host.ctx.suspend();
        status("Stopped.");
    }

    async function restartSource() {
        if (!host.running) return;
        try {
            await startSource();
            onRunning();
        } catch (error) {
            console.error(error);
            status(`Could not switch source: ${error.message}`, true);
        }
    }

    let peakDb = -Infinity;
    let lastFrame = 0;
    function meterLoop(time) {
        const now = 20 * Math.log10(Math.max(host.peak(), 1e-9));
        const fall = lastFrame ? ((time - lastFrame) / 1000) * PEAK_FALL_DB_PER_S : 0;
        lastFrame = time;
        peakDb = Math.max(now, peakDb - fall);
        ui.peak.value = Math.max(-60, peakDb);
        ui.peakValue.textContent = peakDb < -60 ? "−∞ dBFS" : `${peakDb.toFixed(1).replace("-", "−")} dBFS`;
        requestAnimationFrame(meterLoop);
    }

    ui.start.addEventListener("click", () => (host.running ? stop() : start()));
    ui.riff.replaceChildren(...Object.entries(RIFFS).map(([key, riff]) => new Option(riff.label, key, key === "root", key === "root")));
    listDevices().catch(() => ui.device.replaceChildren(new Option("Default input", "")));
    ui.riff.addEventListener("change", restartSource);
    ui.source.addEventListener("change", () => {
        ui.riffRow.hidden = ui.source.value !== "riff";
        ui.fileRow.hidden = ui.source.value !== "file";
        ui.deviceRow.hidden = ui.source.value !== "mic";
        if (ui.source.value === "mic") listDevices().catch(() => {});
        restartSource();
    });
    ui.file.addEventListener("change", () => {
        host.fileBuffer = null;
        restartSource();
    });
    ui.device.addEventListener("change", restartSource);
    navigator.mediaDevices?.addEventListener("devicechange", () => listDevices().catch(() => {}));
    ui.bypass.addEventListener("change", () => host.setBypass(ui.bypass.checked));
    for (const [range, value, key] of [
        [ui.inputTrim, ui.inputTrimValue, "input"],
        [ui.outputTrim, ui.outputTrimValue, "output"],
    ]) {
        range.addEventListener("input", () => {
            value.textContent = `${Number(range.value).toFixed(1).replace("-", "−")} dB`;
            host.setTrim(key, Number(range.value));
        });
    }
    return { enableStart: () => (ui.start.disabled = false) };
}
