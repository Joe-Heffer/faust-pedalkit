// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// The effect designer page.
//
//   diagram (canvas.js, graph.js) -> Faust code (generate.js)
//     -> compiled in a worker (compiler-worker.js)
//     -> a faustwasm node in the shared audio host (../shared/host.js)
//
// A change to the wiring, a block's type, title or a fixed value regenerates
// the code and recompiles it, debounced by COMPILE_DEBOUNCE_MS; the new node
// crossfades in. Moving an exposed control only sets that parameter on the
// running node, with no recompile. The design is kept in localStorage and
// can be exported and imported as JSON.

import { buildControls, flatten, formatValue, rangeInput } from "../shared/controls.js";
import { Host, setupPanel } from "../shared/host.js";
import { BLOCKS, PALETTE, paramsOf } from "./blocks.js";
import { createCanvas } from "./canvas.js";
import { generate } from "./generate.js";
import { addBlock, blockById, disconnect, newGraph, removeBlock, setVariant, validate } from "./graph.js";

// Chosen: long enough that dragging a slider over a fixed value doesn't queue
// a compile per step, short enough that the change is heard within about a
// second (a compile takes 0.2 to 1 s; see docs/usage/designer.md).
const COMPILE_DEBOUNCE_MS = 300;
const STORAGE_KEY = "pedalkit-designer-graph";
const ISSUES_URL = "https://github.com/Joe-Heffer/faust-pedalkit/issues/new";

const $ = (id) => document.getElementById(id);
const ui = {
    palette: $("palette"),
    canvas: $("canvas"),
    deleteButton: $("delete"),
    showCode: $("show-code"),
    exportButton: $("export"),
    importInput: $("import"),
    newButton: $("new"),
    designStatus: $("design-status"),
    warnings: $("warnings"),
    inspector: $("inspector"),
    name: $("fx-name"),
    author: $("fx-author"),
    description: $("fx-description"),
    status: $("status"),
    controls: $("controls"),
    controlsHint: $("controls-hint"),
    readouts: $("readouts"),
    codeDialog: $("code-dialog"),
    code: $("code"),
    codeError: $("code-error"),
    copy: $("copy"),
    download: $("download"),
    closeCode: $("close-code"),
};

let graph = load();
const host = new Host();
let compiled = null; // { code, factory, controls (generator's), meta, latency }
let built = null; // what buildControls returned for the compiled effect
let latencySamples = 0;

function setStatus(el, text, error = false) {
    el.textContent = text;
    el.classList.toggle("error", error);
}

// --- Saving -----------------------------------------------------------------

function load() {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) return validate(JSON.parse(saved));
    } catch (error) {
        console.warn("Could not restore the saved design", error);
    }
    return newGraph();
}

function save() {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(graph));
    } catch {
        // Private windows and blocked storage: the design lives until the tab closes.
    }
}

const slug = () => (graph.name || "effect").toLowerCase().replace(/[^a-z0-9]+/g, "") || "effect";

function downloadText(text, filename, type) {
    const url = URL.createObjectURL(new Blob([text], { type }));
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// --- Compiling --------------------------------------------------------------

const worker = new Worker(new URL("compiler-worker.js", import.meta.url), { type: "module" });
const pending = new Map();
let nextId = 0;
worker.onmessage = ({ data }) => {
    pending.get(data.id)?.(data);
    pending.delete(data.id);
};
worker.onerror = (event) => {
    console.error(event);
    setStatus(ui.designStatus, `The compiler failed to load: ${event.message || "see the browser console"}`, true);
};
const compileInWorker = (name, code) =>
    new Promise((resolve) => {
        const id = nextId++;
        pending.set(id, resolve);
        worker.postMessage({ id, name, code });
    });

let timer = null;
let generation = 0;
const scheduleCompile = () => {
    clearTimeout(timer);
    timer = setTimeout(compileNow, COMPILE_DEBOUNCE_MS);
};

// Generate the code, and compile it if it changed.
async function compileNow() {
    let result;
    try {
        result = generate(graph);
    } catch (error) {
        setStatus(ui.designStatus, error.message, true);
        showWarnings([]);
        return;
    }
    showWarnings(result.warnings);
    // Only the defaults of exposed controls changed: the running node already
    // has those values, so there is nothing to compile.
    if (compiled && withoutSliderDefaults(result.code) === withoutSliderDefaults(compiled.code)) {
        compiled.code = result.code;
        return;
    }
    const mine = ++generation;
    setStatus(ui.designStatus, "Compiling…");
    const reply = await compileInWorker("designer", result.code);
    if (mine !== generation) return; // a newer edit is on its way
    if (reply.error) {
        compiled = null;
        setStatus(ui.designStatus, "The generated code did not compile. This is a bug in the designer: see Code.", true);
        showCode(result.code, reply.error);
        return;
    }
    const factory = { module: reply.module, json: reply.json, soundfiles: {} };
    compiled = { code: result.code, factory, controls: result.controls, meta: JSON.parse(reply.json), latency: result.latency };
    rebuildControls();
    setStatus(ui.designStatus, `Compiled in ${Math.round(reply.ms)} ms · latency ${result.latency} samples`);
    if (host.ctx) {
        await host.setEffect(factory, "designer");
        showRunning();
    }
}

// The code with every hslider's default replaced, to compare two versions.
const withoutSliderDefaults = (code) => code.replace(/(hslider\("[^"]*",\s*)[-\d.e]+/g, "$1#");

// --- Controls of the compiled effect ----------------------------------------

// The block parameter behind each exposed control, by Faust address.
function controlTargets() {
    const byLabel = Object.fromEntries(compiled.controls.map((c) => [c.label, c]));
    const targets = {};
    for (const item of flatten(compiled.meta.ui)) if (byLabel[item.label]) targets[item.address] = byLabel[item.label];
    return targets;
}

function rebuildControls() {
    const targets = controlTargets();
    const initial = {};
    for (const [address, c] of Object.entries(targets)) initial[address] = blockById(graph, c.block).params[c.key].value;
    host.values = {};
    latencySamples = 0;
    built = buildControls(
        compiled.meta,
        ui.controls,
        ui.readouts,
        (address, value) => {
            host.setParam(address, value);
            const target = targets[address];
            if (!target) return;
            const block = blockById(graph, target.block);
            if (block && block.params[target.key].value !== value) {
                block.params[target.key].value = value;
                save();
            }
        },
        initial,
    );
    ui.controlsHint.hidden = compiled.controls.length > 0;
}

host.onOutputParam = (address, value) => {
    const readout = built?.readouts[address];
    if (readout) readout.dd.textContent = formatValue(value, readout.item);
    if (address === built?.latencyAddress && value !== latencySamples) {
        latencySamples = value;
        host.setLatency(latencySamples);
        showRunning();
    }
};

function showRunning() {
    if (!host.running || !host.effect) return;
    setStatus(ui.status, `Running · ${host.backend} · ${host.ctx.sampleRate} Hz · latency ${latencySamples} samples`);
}

// --- Inspector --------------------------------------------------------------

function showWarnings(warnings) {
    ui.warnings.replaceChildren(
        ...warnings.map((w) => {
            const li = document.createElement("li");
            li.textContent = w;
            return li;
        }),
    );
}

function renderInspector() {
    const sel = canvas.selection;
    ui.deleteButton.disabled = !sel || (sel.block && BLOCKS[blockById(graph, sel.block).type].fixed);
    const box = ui.inspector;
    box.replaceChildren();
    const hint = (text) => {
        const p = document.createElement("p");
        p.className = "hint";
        p.textContent = text;
        box.append(p);
    };
    if (!sel) return hint("Select a block to set it up.");
    if (sel.wire) return hint("A wire. Delete it with the button below the diagram, or the Delete key.");
    const block = blockById(graph, sel.block);
    const def = BLOCKS[block.type];
    if (def.fixed) return hint(block.type === "input" ? "The effect's input." : "The effect's output. The designer always ends it with a safety limiter.");

    const title = document.createElement("input");
    title.type = "text";
    title.value = block.title;
    title.maxLength = 30;
    title.id = "block-title";
    title.addEventListener("change", () => {
        block.title = title.value.trim() || def.label;
        changed("structure");
    });
    box.append(row("Title", title));

    if (def.variants) {
        const select = document.createElement("select");
        select.id = "block-variant";
        for (const [key, v] of Object.entries(def.variants)) select.append(new Option(v.label, key, false, key === block.variant));
        select.addEventListener("change", () => {
            setVariant(block, select.value);
            changed("structure");
            renderInspector();
        });
        box.append(row("Type", select));
    }

    for (const param of paramsOf(block)) box.append(paramEditor(block, param));
    if (!paramsOf(block).length) hint("No parameters.");
}

function row(text, input) {
    const div = document.createElement("div");
    div.className = "row";
    const label = document.createElement("label");
    label.htmlFor = input.id;
    label.textContent = text;
    div.append(label, input);
    return div;
}

function paramEditor(block, param) {
    const state = block.params[param.key];
    const item = { ...param, label: param.label, meta: [{ unit: param.unit }, ...(param.log ? [{ scale: "log" }] : [])] };
    const wrap = document.createElement("div");
    wrap.className = "control param";
    const id = `param-${block.id}-${param.key}`;
    const label = document.createElement("label");
    label.htmlFor = id;
    const output = document.createElement("output");
    const range = rangeInput(item);
    range.input.id = id;
    range.set(state.value);
    range.input.disabled = state.exposed;
    const show = () => (output.textContent = state.exposed ? "set in Controls" : formatValue(range.get(), item));
    show();
    range.input.addEventListener("input", () => {
        state.value = range.get();
        show();
        changed("value");
    });
    label.append(param.label, output);

    const expose = document.createElement("label");
    expose.className = "expose";
    const box = document.createElement("input");
    box.type = "checkbox";
    box.checked = state.exposed;
    box.addEventListener("change", () => {
        state.exposed = box.checked;
        range.input.disabled = state.exposed;
        show();
        changed("structure");
    });
    expose.append(box, "Expose as a control");
    expose.title = param.tooltip;
    wrap.append(label, range.input, expose);
    return wrap;
}

// --- Editing ----------------------------------------------------------------

// kind: "move" (layout), "value" (a fixed value) or "structure".
function changed(kind) {
    save();
    if (kind !== "move") {
        canvas.render();
        scheduleCompile();
    }
}

const canvas = createCanvas(ui.canvas, () => graph, {
    onSelect: renderInspector,
    onChange: changed,
    onError: (message) => setStatus(ui.designStatus, `Not connected: ${message}.`, true),
});

function deleteSelection() {
    const sel = canvas.selection;
    if (!sel) return;
    if (sel.wire) disconnect(graph, sel.wire);
    else if (!removeBlock(graph, sel.block)) return;
    canvas.select(null);
    changed("structure");
}

for (const type of PALETTE) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary";
    button.textContent = BLOCKS[type].label;
    button.addEventListener("click", () => {
        const { x, y } = canvas.freeSpot();
        const block = addBlock(graph, type, x, y);
        canvas.select({ block: block.id });
        changed("structure");
    });
    ui.palette.append(button);
}

ui.deleteButton.addEventListener("click", deleteSelection);
ui.canvas.addEventListener("keydown", (event) => {
    if (event.key === "Delete" || event.key === "Backspace") {
        event.preventDefault();
        deleteSelection();
    }
});

function showEffectFields() {
    ui.name.value = graph.name || "";
    ui.author.value = graph.author || "";
    ui.description.value = graph.description || "";
}
for (const [input, key] of [
    [ui.name, "name"],
    [ui.author, "author"],
    [ui.description, "description"],
]) {
    input.addEventListener("change", () => {
        graph[key] = input.value.trim();
        changed("structure");
    });
}

function replaceGraph(next) {
    graph = next;
    compiled = null;
    showEffectFields();
    canvas.select(null);
    changed("structure");
}

ui.newButton.addEventListener("click", () => {
    if (confirm("Start a new design? Export this one first if you want to keep it.")) replaceGraph(newGraph());
});
ui.exportButton.addEventListener("click", () => downloadText(`${JSON.stringify(graph, null, 2)}\n`, `${slug()}.json`, "application/json"));
ui.importInput.addEventListener("change", async () => {
    const file = ui.importInput.files[0];
    ui.importInput.value = "";
    if (!file) return;
    try {
        replaceGraph(validate(JSON.parse(await file.text())));
    } catch (error) {
        setStatus(ui.designStatus, `Could not import ${file.name}: ${error.message}`, true);
    }
});

// --- Code panel -------------------------------------------------------------

function showCode(code, error = null) {
    ui.code.textContent = code;
    ui.codeError.hidden = !error;
    if (error) {
        ui.codeError.replaceChildren(
            `The generated code did not compile, which is a bug in the designer. Please `,
            Object.assign(document.createElement("a"), { href: ISSUES_URL, textContent: "report it", target: "_blank", rel: "noopener" }),
            ` with this code and an export of your design. Compiler message: ${error}`,
        );
    }
    if (!ui.codeDialog.open) ui.codeDialog.showModal();
}

ui.showCode.addEventListener("click", () => {
    try {
        showCode(generate(graph).code);
    } catch (error) {
        setStatus(ui.designStatus, error.message, true);
    }
});
ui.copy.addEventListener("click", async () => {
    try {
        await navigator.clipboard.writeText(ui.code.textContent);
        ui.copy.textContent = "Copied";
    } catch {
        ui.copy.textContent = "Copy failed";
    }
    setTimeout(() => (ui.copy.textContent = "Copy"), 1500);
});
ui.download.addEventListener("click", () => downloadText(ui.code.textContent, `${slug()}.dsp`, "text/plain"));
ui.closeCode.addEventListener("click", () => ui.codeDialog.close());

// --- Start-up ---------------------------------------------------------------

const panel = setupPanel(host, {
    prepare: async () => {
        if (compiled) await host.setEffect(compiled.factory, "designer");
    },
    status: (text, error) => setStatus(ui.status, text, error),
    onRunning: showRunning,
});

showEffectFields();
renderInspector();
if (!window.AudioContext) {
    setStatus(ui.status, "This browser has no Web Audio support.", true);
} else {
    panel.enableStart();
}
compileNow();
