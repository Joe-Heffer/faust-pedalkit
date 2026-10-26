// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// Browser demo for the Faust Pedal Kit effects.
//
// The audio graph, sources, levels and bypass are in shared/host.js (shared
// with the effect designer); see the signal flow there. This page loads the
// effects `make web` compiled (build/web/<name>/dsp-module.wasm) and builds
// each one's controls from its dsp-meta.json, the same description
// `make describe` writes.

import { buildControls, formatValue, metaValue } from "./shared/controls.js";
import { Host, setupPanel } from "./shared/host.js";

const $ = (id) => document.getElementById(id);
const ui = {
    effect: $("effect"),
    description: $("effect-description"),
    status: $("status"),
    controls: $("controls"),
    readouts: $("readouts"),
    reset: $("reset"),
};

// Effect descriptions loaded from build/web/<name>/dsp-meta.json, by name.
const metas = {};
const host = new Host();
let controls = null; // what buildControls returned for the selected effect
let latencySamples = 0;

function setStatus(text, error = false) {
    ui.status.textContent = text;
    ui.status.classList.toggle("error", error);
}

async function loadMeta(name) {
    if (!metas[name]) {
        const response = await fetch(`${name}/dsp-meta.json`);
        if (!response.ok) throw new Error(`${name}/dsp-meta.json: HTTP ${response.status}`);
        metas[name] = await response.json();
    }
    return metas[name];
}

host.onOutputParam = (address, value) => {
    const readout = controls?.readouts[address];
    if (readout) readout.dd.textContent = formatValue(value, readout.item);
    if (address === controls?.latencyAddress && value !== latencySamples) {
        latencySamples = value;
        host.setLatency(latencySamples);
        showRunning();
    }
};

function showRunning() {
    if (!host.running || !host.effect) return;
    const meta = metas[ui.effect.value];
    const latency = latencySamples
        ? ` · latency ${latencySamples} samples (${((1000 * latencySamples) / host.ctx.sampleRate).toFixed(2)} ms)`
        : "";
    setStatus(`Running ${meta.name} ${metaValue(meta, "version") || ""} · ${host.backend} · ${host.ctx.sampleRate} Hz${latency}`);
}

async function loadEffect(name) {
    const meta = await loadMeta(name);
    const response = await fetch(`${name}/dsp-module.wasm`);
    if (!response.ok) throw new Error(`${name}/dsp-module.wasm: HTTP ${response.status}`);
    const module = await WebAssembly.compile(await response.arrayBuffer());
    await host.setEffect({ module, json: JSON.stringify(meta), soundfiles: {} }, name);
}

async function selectEffect() {
    const name = ui.effect.value;
    ui.effect.disabled = true;
    try {
        const meta = await loadMeta(name);
        ui.description.textContent = metaValue(meta, "description") || "";
        host.values = {};
        latencySamples = 0;
        controls = buildControls(meta, ui.controls, ui.readouts, (address, value) => host.setParam(address, value));
        if (host.ctx) {
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

const panel = setupPanel(host, {
    prepare: () => loadEffect(ui.effect.value),
    status: setStatus,
    onRunning: showRunning,
});
ui.effect.addEventListener("change", selectEffect);
ui.reset.addEventListener("click", () => controls?.reset());

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
        panel.enableStart();
    } catch (error) {
        console.error(error);
        setStatus(`Could not load the effects: ${error.message}`, true);
    }
})();
