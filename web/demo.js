// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// Browser demo for the Faust Pedal Kit effects.
//
// Signal flow (all Web Audio nodes, mono):
//
//   source -> input trim -+-> effect (faustwasm AudioWorklet) -> wet gain -+-> output trim -> analyser -> speakers
//                         +-> delay (effect latency) ---------> dry gain --+
//
// The source is a synthesised test riff, a looping audio file or a live
// input. The effect's controls are built from its dsp-meta.json, the same
// description `make describe` writes. The dry path is delayed by the latency
// the effect reports, so Bypass switches between time-aligned signals.

import { FaustMonoDspGenerator } from "./faustwasm/index.js";

// Chosen values (see docs/usage/browser.md).
const RIFF_PEAK_DB = -10; // test riff peak level, a typical bass DI peak
const RIFF_ROOT_HZ = 41.2034; // low E on a four-string bass (E1)
// Original riffs, chosen to show different sides of a bass effect. Notes are
// semitones above the root, one per step (null is a rest), and a step is an
// eighth note at `bpm`. `decay` scales how fast the pluck dies away (1 is a
// plucked string; lower rings on, like a sustained note) and `sub` mixes in a
// sine an octave below, for a synth-bass weight. All values are chosen.
const RIFFS = {
    root: {
        label: "Root and octave (E)",
        bpm: 100,
        decay: 1,
        sub: 0,
        // Open E and the octave, where bass drive matters most.
        notes: [0, 0, 12, 0, 3, 0, 5, 7, 0, 0, 12, 0, 10, 7, 5, 3],
    },
    walking: {
        label: "Walking line (A minor)",
        bpm: 120,
        decay: 0.8,
        sub: 0,
        // Quarter-note walk through A minor: A C D E G E D C (A is 5 semitones up).
        notes: [5, null, 8, null, 10, null, 12, null, 15, null, 12, null, 10, null, 8, null],
    },
    octaves: {
        label: "Octave pulse (disco)",
        bpm: 116,
        decay: 1.2,
        sub: 0,
        // Offbeat octave jumps on a pedal E, with a dropped note in the last bar.
        notes: [0, 12, 0, 12, 0, 12, 0, 12, 3, 15, 3, 15, 5, 17, 7, null],
    },
    sustained: {
        label: "Slow sustained notes",
        bpm: 70,
        decay: 0.15,
        sub: 0,
        // Long held notes expose compression, sustain and low-end tracking.
        notes: [0, null, null, null, 7, null, null, null, 5, null, null, null, 3, null, null, null],
    },
    synth: {
        label: "Synth bass (sub octave)",
        bpm: 105,
        decay: 0.35,
        sub: 0.8,
        // Syncopated 16th-note line an octave up, with a sine sub under each note.
        notes: [12, null, 12, 12, null, 15, null, 12, 17, null, 12, null, 10, null, 12, 7],
        step16: true,
    },
    slap: {
        label: "Funk slap (staccato)",
        bpm: 98,
        decay: 3,
        sub: 0,
        // Short bright notes with gaps: heavy on attack transients.
        notes: [0, null, 12, 0, null, 0, 12, null, 3, null, 5, 5, null, 7, 12, null],
        step16: true,
    },
};
const BYPASS_FADE_S = 0.01; // crossfade time constant for Bypass, avoids clicks
const PEAK_FALL_DB_PER_S = 20; // peak meter release

const $ = (id) => document.getElementById(id);
const ui = {
    effect: $("effect"),
    description: $("effect-description"),
    source: $("source"),
    riffRow: $("riff-row"),
    riff: $("riff"),
    fileRow: $("file-row"),
    file: $("file"),
    deviceRow: $("device-row"),
    device: $("device"),
    start: $("start"),
    bypass: $("bypass"),
    status: $("status"),
    controls: $("controls"),
    readouts: $("readouts"),
    reset: $("reset"),
    inputTrim: $("input-trim"),
    inputTrimValue: $("input-trim-value"),
    outputTrim: $("output-trim"),
    outputTrimValue: $("output-trim-value"),
    peak: $("peak"),
    peakValue: $("peak-value"),
};

// Effect descriptions loaded from build/web/<name>/dsp-meta.json, by name.
const metas = {};
// Current control values for the selected effect, by Faust address.
let values = {};
// Read-only outputs (bargraphs) by address, as <dd> elements.
let readouts = {};
let latencyAddress = null;
let latencySamples = 0;

// Audio graph, created on the first Start (browsers only allow audio after a
// user gesture).
let ctx = null;
let graph = null;
let effectNode = null;
let effectBackend = "";
let sourceNode = null;
let micStream = null;
const riffBuffers = {}; // rendered riffs by key, made on first use
let fileBuffer = null;
let running = false;

const dbToGain = (db) => 10 ** (db / 20);
const metaValue = (meta, key) => (meta.meta || []).map((m) => m[key]).find((v) => v !== undefined);
const itemMeta = (item, key) => (item.meta || []).map((m) => m[key]).find((v) => v !== undefined);

function setStatus(text, error = false) {
    ui.status.textContent = text;
    ui.status.classList.toggle("error", error);
}

function formatValue(value, item) {
    const step = item.step || 1;
    const decimals = Math.max(0, Math.min(3, -Math.floor(Math.log10(step))));
    const unit = itemMeta(item, "unit");
    const number = value.toFixed(decimals).replace("-", "−");
    return unit ? `${number} ${unit}` : number;
}

// Flatten the Faust UI tree into its controls, in declaration order (Faust
// has already sorted them by their [n] prefixes).
function flatten(items, out = []) {
    for (const item of items) {
        if (item.items) flatten(item.items, out);
        else out.push(item);
    }
    return out;
}

async function loadMeta(name) {
    if (!metas[name]) {
        const response = await fetch(`${name}/dsp-meta.json`);
        if (!response.ok) throw new Error(`${name}/dsp-meta.json: HTTP ${response.status}`);
        metas[name] = await response.json();
    }
    return metas[name];
}

function setParam(address, value) {
    values[address] = value;
    if (effectNode) effectNode.setParamValue(address, value);
}

function buildControls(meta) {
    ui.controls.replaceChildren();
    ui.readouts.replaceChildren();
    values = {};
    readouts = {};
    latencyAddress = null;
    latencySamples = 0;

    for (const item of flatten(meta.ui)) {
        const id = `ctl-${item.address.replace(/[^A-Za-z0-9]/g, "-")}`;
        const tooltip = itemMeta(item, "tooltip");

        if (item.type === "hbargraph" || item.type === "vbargraph") {
            const dt = document.createElement("dt");
            dt.textContent = item.label;
            const dd = document.createElement("dd");
            dd.textContent = "–";
            ui.readouts.append(dt, dd);
            readouts[item.address] = { item, dd };
            if ((item.meta || []).some((m) => m.lv2 === "reportsLatency")) latencyAddress = item.address;
            continue;
        }

        const wrap = document.createElement("div");
        wrap.className = "control";
        const label = document.createElement("label");
        label.htmlFor = id;
        const input = document.createElement("input");
        input.id = id;

        if (item.type === "checkbox" || item.type === "button") {
            wrap.classList.add("checkbox");
            input.type = "checkbox";
            label.append(input, ` ${item.label}`);
            values[item.address] = 0;
            input.addEventListener("change", () => setParam(item.address, input.checked ? 1 : 0));
            wrap.reset = () => {
                input.checked = false;
                setParam(item.address, 0);
            };
            wrap.append(label);
        } else {
            // hslider, vslider and nentry all become a horizontal range input.
            const output = document.createElement("output");
            output.htmlFor = id;
            input.type = "range";
            input.min = item.min;
            input.max = item.max;
            input.step = item.step;
            input.value = item.init;
            const show = () => {
                output.textContent = formatValue(Number(input.value), item);
                input.setAttribute("aria-valuetext", output.textContent);
            };
            show();
            values[item.address] = item.init;
            input.addEventListener("input", () => {
                show();
                setParam(item.address, Number(input.value));
            });
            wrap.reset = () => {
                input.value = item.init;
                show();
                setParam(item.address, item.init);
            };
            label.append(item.label, output);
            wrap.append(label, input);
        }

        if (tooltip) {
            const hint = document.createElement("div");
            hint.className = "hint";
            hint.id = `${id}-hint`;
            hint.textContent = tooltip;
            input.setAttribute("aria-describedby", hint.id);
            wrap.append(hint);
        }
        ui.controls.append(wrap);
    }
}

function onOutputParam(address, value) {
    const readout = readouts[address];
    if (readout) readout.dd.textContent = formatValue(value, readout.item);
    if (address === latencyAddress && value !== latencySamples) {
        latencySamples = value;
        if (graph) graph.dryDelay.delayTime.value = latencySamples / ctx.sampleRate;
        showRunning();
    }
}

function showRunning() {
    if (!running || !effectNode) return;
    const meta = metas[ui.effect.value];
    const latency = latencySamples
        ? ` · latency ${latencySamples} samples (${((1000 * latencySamples) / ctx.sampleRate).toFixed(2)} ms)`
        : "";
    setStatus(`Running ${meta.name} ${metaValue(meta, "version") || ""} · ${effectBackend} · ${ctx.sampleRate} Hz${latency}`);
}

// Synthesised bass riffs, so the demo makes a sound with no file and no
// committed audio. Each note is a sum of harmonics at 1/k amplitude (a
// sawtooth-like pluck) whose upper harmonics die away faster, roughly as a
// plucked string's do. A riff may also add a sine an octave below.
function makeRiff(sampleRate, riff) {
    const step = (60 / riff.bpm / 2) / (riff.step16 ? 2 : 1);
    const noteLen = Math.round(step * sampleRate);
    const buffer = new AudioBuffer({ length: noteLen * riff.notes.length, sampleRate, numberOfChannels: 1 });
    const y = buffer.getChannelData(0);
    const attack = Math.round(0.002 * sampleRate);
    const release = Math.round(0.02 * sampleRate);
    riff.notes.forEach((semitones, n) => {
        if (semitones === null) return;
        const f = RIFF_ROOT_HZ * 2 ** (semitones / 12);
        const offset = n * noteLen;
        // A note rings through the rests that follow it.
        let steps = 1;
        while (n + steps < riff.notes.length && riff.notes[n + steps] === null) steps++;
        const len = steps * noteLen;
        const note = new Float32Array(len);
        for (let k = 1; k * f < 5000; k++) {
            const w = (2 * Math.PI * k * f) / sampleRate;
            const decay = Math.exp((-(2 + 0.8 * k) * riff.decay) / sampleRate);
            let amp = 1 / k;
            for (let i = 0; i < len; i++) {
                note[i] += amp * Math.sin(w * i);
                amp *= decay;
            }
        }
        if (riff.sub) {
            const w = (2 * Math.PI * f) / (2 * sampleRate);
            const decay = Math.exp((-2 * riff.decay) / sampleRate);
            let amp = riff.sub;
            for (let i = 0; i < len; i++) {
                note[i] += amp * Math.sin(w * i);
                amp *= decay;
            }
        }
        for (let i = 0; i < attack; i++) note[i] *= i / attack;
        for (let i = 0; i < release; i++) note[len - 1 - i] *= i / release;
        for (let i = 0; i < len; i++) y[offset + i] += note[i];
    });
    let peak = 0;
    for (const v of y) peak = Math.max(peak, Math.abs(v));
    const scale = dbToGain(RIFF_PEAK_DB) / peak;
    for (let i = 0; i < y.length; i++) y[i] *= scale;
    return buffer;
}

function buildGraph() {
    const input = new GainNode(ctx, {
        gain: dbToGain(Number(ui.inputTrim.value)),
        channelCount: 1,
        channelCountMode: "explicit",
        channelInterpretation: "speakers",
    });
    const dryDelay = new DelayNode(ctx, { maxDelayTime: 0.1 });
    const dry = new GainNode(ctx, { gain: ui.bypass.checked ? 1 : 0 });
    const wet = new GainNode(ctx, { gain: ui.bypass.checked ? 0 : 1 });
    const output = new GainNode(ctx, { gain: dbToGain(Number(ui.outputTrim.value)) });
    const analyser = new AnalyserNode(ctx, { fftSize: 2048 });
    input.connect(dryDelay).connect(dry).connect(output);
    wet.connect(output);
    output.connect(analyser).connect(ctx.destination);
    graph = { input, dryDelay, dry, wet, output, analyser };
    requestAnimationFrame(meterLoop);
}

let peakDb = -Infinity;
let lastFrame = 0;
function meterLoop(time) {
    const data = new Float32Array(graph.analyser.fftSize);
    graph.analyser.getFloatTimeDomainData(data);
    let peak = 0;
    // A suspended context leaves its last block in the analyser, so only
    // read it while running.
    if (running) for (const v of data) peak = Math.max(peak, Math.abs(v));
    const now = 20 * Math.log10(Math.max(peak, 1e-9));
    const fall = lastFrame ? ((time - lastFrame) / 1000) * PEAK_FALL_DB_PER_S : 0;
    lastFrame = time;
    peakDb = Math.max(now, peakDb - fall);
    ui.peak.value = Math.max(-60, peakDb);
    ui.peakValue.textContent = peakDb < -60 ? "−∞ dBFS" : `${peakDb.toFixed(1).replace("-", "−")} dBFS`;
    requestAnimationFrame(meterLoop);
}

async function loadEffect(name) {
    const meta = await loadMeta(name);
    const response = await fetch(`${name}/dsp-module.wasm`);
    if (!response.ok) throw new Error(`${name}/dsp-module.wasm: HTTP ${response.status}`);
    const module = await WebAssembly.compile(await response.arrayBuffer());
    const factory = { module, json: JSON.stringify(meta), soundfiles: {} };
    const generator = new FaustMonoDspGenerator();
    let node = null;
    try {
        node = await generator.createNode(ctx, name, factory, false);
        effectBackend = "AudioWorklet";
    } catch (error) {
        console.warn("AudioWorklet node failed, falling back to ScriptProcessor", error);
    }
    if (!node) {
        node = await generator.createNode(ctx, name, factory, true, 512);
        effectBackend = "ScriptProcessor (fallback)";
    }
    if (!node) throw new Error(`could not create the ${meta.name} node`);
    for (const [address, value] of Object.entries(values)) node.setParamValue(address, value);
    node.setOutputParamHandler(onOutputParam);

    graph.input.connect(node).connect(graph.wet);
    const old = effectNode;
    effectNode = node;
    if (old) {
        old.disconnect();
        graph.input.disconnect(old);
        old.destroy();
    }
}

function stopSource() {
    if (sourceNode) {
        if (sourceNode.stop) sourceNode.stop();
        sourceNode.disconnect();
        sourceNode = null;
    }
    if (micStream) {
        for (const track of micStream.getTracks()) track.stop();
        micStream = null;
    }
}

async function listDevices() {
    const devices = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "audioinput");
    const selected = ui.device.value;
    // Before permission is granted the browser may list no inputs, or inputs
    // without labels, so always offer the default input as well.
    ui.device.replaceChildren(
        new Option("Default input", "", false, !selected),
        ...devices
            .filter((d) => d.deviceId && d.deviceId !== "default")
            .map((d, i) => new Option(d.label || `Input ${i + 1}`, d.deviceId, false, d.deviceId === selected)),
    );
}

async function startSource() {
    stopSource();
    const kind = ui.source.value;
    if (kind === "mic") {
        if (!navigator.mediaDevices?.getUserMedia) throw new Error("this browser offers no audio input here (it needs HTTPS)");
        micStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                deviceId: ui.device.value ? { exact: ui.device.value } : undefined,
                echoCancellation: false,
                noiseSuppression: false,
                autoGainControl: false,
            },
        });
        sourceNode = new MediaStreamAudioSourceNode(ctx, { mediaStream: micStream });
        await listDevices();
    } else {
        let buffer;
        if (kind === "file") {
            if (!fileBuffer && ui.file.files[0]) fileBuffer = await ctx.decodeAudioData(await ui.file.files[0].arrayBuffer());
            if (!fileBuffer) throw new Error("choose an audio file first");
            buffer = fileBuffer;
        } else {
            const key = ui.riff.value;
            riffBuffers[key] ??= makeRiff(ctx.sampleRate, RIFFS[key]);
            buffer = riffBuffers[key];
        }
        sourceNode = new AudioBufferSourceNode(ctx, { buffer, loop: true });
        sourceNode.start();
    }
    sourceNode.connect(graph.input);
}

async function start() {
    ui.start.disabled = true;
    try {
        if (!ctx) {
            setStatus("Starting audio…");
            ctx = new AudioContext({ latencyHint: "interactive" });
            buildGraph();
            await loadEffect(ui.effect.value);
        }
        await ctx.resume();
        await startSource();
        running = true;
        ui.start.textContent = "Stop";
        showRunning();
    } catch (error) {
        console.error(error);
        setStatus(`Could not start: ${error.message}`, true);
    } finally {
        ui.start.disabled = false;
    }
}

async function stop() {
    stopSource();
    running = false;
    ui.start.textContent = "Start";
    if (ctx) await ctx.suspend();
    setStatus("Stopped.");
}

async function selectEffect() {
    const name = ui.effect.value;
    ui.effect.disabled = true;
    try {
        const meta = await loadMeta(name);
        ui.description.textContent = metaValue(meta, "description") || "";
        buildControls(meta);
        if (ctx) {
            await loadEffect(name);
            showRunning();
        } else {
            setStatus("Ready. Press Start.");
        }
    } catch (error) {
        console.error(error);
        setStatus(`Could not load ${name}: ${error.message}`, true);
    } finally {
        ui.effect.disabled = false;
    }
}

async function restartSource() {
    if (!running) return;
    try {
        await startSource();
        showRunning();
    } catch (error) {
        console.error(error);
        setStatus(`Could not switch source: ${error.message}`, true);
    }
}

ui.start.addEventListener("click", () => (running ? stop() : start()));
ui.effect.addEventListener("change", selectEffect);
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
    fileBuffer = null;
    restartSource();
});
ui.device.addEventListener("change", restartSource);
navigator.mediaDevices?.addEventListener("devicechange", () => listDevices().catch(() => {}));
ui.bypass.addEventListener("change", () => {
    if (!graph) return;
    const t = ctx.currentTime;
    graph.dry.gain.setTargetAtTime(ui.bypass.checked ? 1 : 0, t, BYPASS_FADE_S);
    graph.wet.gain.setTargetAtTime(ui.bypass.checked ? 0 : 1, t, BYPASS_FADE_S);
});
for (const [range, value, key] of [
    [ui.inputTrim, ui.inputTrimValue, "input"],
    [ui.outputTrim, ui.outputTrimValue, "output"],
]) {
    range.addEventListener("input", () => {
        value.textContent = `${Number(range.value).toFixed(1).replace("-", "−")} dB`;
        if (graph) graph[key].gain.setTargetAtTime(dbToGain(Number(range.value)), ctx.currentTime, 0.01);
    });
}
ui.reset.addEventListener("click", () => {
    for (const control of ui.controls.children) control.reset?.();
});

// Start-up: list the effects that `make web` built.
(async () => {
    try {
        if (!window.AudioContext) throw new Error("this browser has no Web Audio support");
        const names = await (await fetch("effects.json")).json();
        await Promise.all(names.map(loadMeta));
        ui.effect.replaceChildren(...names.map((name) => new Option(metas[name].name, name)));
        const wanted = new URLSearchParams(location.search).get("fx");
        if (names.includes(wanted)) ui.effect.value = wanted;
        await selectEffect();
        ui.start.disabled = false;
    } catch (error) {
        console.error(error);
        setStatus(`Could not load the effects: ${error.message}`, true);
    }
})();
