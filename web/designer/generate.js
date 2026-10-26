// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// Turns a designer graph (graph.js) into a Faust .dsp that follows the rules
// in AGENTS.md, so the user never has to:
//
// * each block becomes a named signal inside a `with` block, in processing
//   order; a fan-out is a name used twice, and a Mix adds its inputs
// * waveshapers run inside pk.oversample4 (the templates in blocks.js do this)
//   and filters stay outside
// * every path's latency is tracked; where paths with different latencies
//   meet, the shorter one is delayed by the difference, so blends don't comb
// * the total latency is reported with the `[lv2:reportsLatency]` bargraph
// * fixed values become named constants and exposed ones smoothed sliders
// * the output always ends in pk.safety(0.989)
//
// generate(graph, options) returns { code, latency, controls, warnings }, or
// throws when the graph can't make a sound (Output not connected).

import { BLOCKS, paramsOf, templateOf } from "./blocks.js";
import { processingOrder, wireInto } from "./graph.js";

// pk.os4Latency in src/lib/pedalkit.lib; tests/web/test_designer.mjs checks
// that the compiled effect reports what the generator expects.
export const OS4_LATENCY = 32;

const SAFETY_CEILING = 0.989; // as every effect in src/ (AGENTS.md)
const MAX_LATENCY = 128; // samples, the limit tests/common/test_latency.py sets

const upperFirst = (s) => s[0].toUpperCase() + s.slice(1);
// Faust labels and metadata are delimited by quotes and square brackets.
const clean = (s) => String(s).replace(/["[\]\\]/g, "").replace(/\s+/g, " ").trim();

// A number as a Faust float literal, so no expression does integer division.
function literal(value) {
    const s = String(Number(value));
    return /[.e]/.test(s) ? s : `${s}.0`;
}

// The name of a block's output signal inside `effect`. The Input block is the
// effect's argument.
const signal = (id) => (id === "input" ? "x" : id);

function lv2class(blocks) {
    if (blocks.some((b) => b.type === "waveshaper")) return "DistortionPlugin";
    if (blocks.some((b) => b.type === "filter")) return "FilterPlugin";
    return "UtilityPlugin";
}

// A Faust expression for `n` oversampler delays.
const delayExpr = (n) => (n === 1 ? "pk.os4Latency" : `${n} * pk.os4Latency`);

// options.author is used when the graph names none.
export function generate(graph, { author: fallbackAuthor = "Pedal Kit designer user", year = new Date().getFullYear() } = {}) {
    const author = clean(graph.author || "") || fallbackAuthor;
    if (!wireInto(graph, "output", 0)) throw new Error("Connect a block to Output to hear the effect.");

    const order = processingOrder(graph).filter((b) => b.type !== "output");
    const warnings = [];
    const constants = [];
    const controls = [];
    const labels = new Set();
    const lines = [];
    const flow = [];
    // Latency of each block's output, in oversampler delays (pk.os4Latency).
    const delays = { input: 0 };

    for (const block of order) {
        if (block.type === "input") continue;
        const def = BLOCKS[block.type];

        // Parameters: a named constant, or an exposed and smoothed control.
        const p = {};
        for (const param of paramsOf(block)) {
            const name = `${block.id}${upperFirst(param.key)}`;
            const { value, exposed } = block.params[param.key];
            const unit = param.unit ? ` ${param.unit}` : "";
            if (exposed) {
                // "Tone Frequency", but just "Drive" for a block titled Drive.
                const base = block.title.toLowerCase().includes(param.label.toLowerCase())
                    ? clean(block.title)
                    : clean(`${block.title} ${param.label}`);
                let label = base;
                for (let n = 2; labels.has(label); n++) label = `${base} ${n}`;
                labels.add(label);
                const meta = [`[unit:${param.unit}]`];
                if (param.log) meta.push("[scale:log]");
                meta.push(`[tooltip:${clean(param.tooltip)}]`);
                const index = controls.length;
                controls.push({ label, block: block.id, key: param.key, unit: param.unit, min: param.min, max: param.max, init: value });
                constants.push({
                    exposed: true,
                    text:
                        `${name} = hslider("[${index}]${label} ${meta.join(" ")}",\n` +
                        `    ${literal(value)}, ${literal(param.min)}, ${literal(param.max)}, ${literal(param.step)}) : si.smoo;`,
                });
            } else {
                constants.push({ exposed: false, text: `${name} = ${literal(value)}; //${unit}, chosen in the designer` });
            }
            p[param.key] = param.to ? param.to(name) : name;
        }

        // Inputs, with the shorter paths delayed to match the longest.
        const sources = def.inputs.map((_, port) => wireInto(graph, block.id, port)?.from);
        const arrive = Math.max(0, ...sources.filter(Boolean).map((id) => delays[id]));
        const ins = sources.map((id, port) => {
            if (!id) {
                warnings.push(`${block.title}: input ${def.inputs[port]} is not connected, so it gets silence.`);
                return "0";
            }
            const lag = arrive - delays[id];
            return lag ? `(${signal(id)} : @(${delayExpr(lag)}))` : signal(id);
        });
        delays[block.id] = arrive + (def.oversampled ? 1 : 0);

        lines.push(`    ${signal(block.id)} = ${templateOf(block)(p, ins)};`);
        const variant = def.variants ? ` (${def.variants[block.variant].label})` : "";
        const from = sources.map((id, port) => {
            if (!id) return "silence";
            const lag = arrive - delays[id];
            return lag ? `${id} delayed ${lag * OS4_LATENCY}` : id;
        });
        const extra = def.oversampled ? `, 4x oversampled, +${OS4_LATENCY} samples` : "";
        flow.push(`//   ${block.id}: ${def.label}${variant} <- ${from.join(", ")}${extra}`);
    }

    const last = wireInto(graph, "output", 0).from;
    const latency = delays[last] * OS4_LATENCY;
    flow.push(`//   output <- ${last}, then the safety limiter`);
    if (latency > MAX_LATENCY) {
        warnings.push(`Latency is ${latency} samples; effects in this repo stay within ${MAX_LATENCY}. Put fewer waveshapers in series.`);
    }

    const exposedConstants = constants.filter((c) => c.exposed).map((c) => c.text);
    const fixedConstants = constants.filter((c) => !c.exposed).map((c) => c.text);
    const name = clean(graph.name) || "Untitled";
    const description = clean(graph.description) || "Designed in the Pedal Kit effect designer";

    // The generated file's own licence header, not this file's.
    // REUSE-IgnoreStart
    const header = [`// SPDX-FileCopyrightText: ${year} ${clean(author)}`, "// SPDX-License-Identifier: MIT"];
    // REUSE-IgnoreEnd
    const code = [
        ...header,
        `// ${name}: generated by the Pedal Kit effect designer from a block diagram.`,
        "// Every value below was chosen in the designer. To make this a new effect,",
        "// follow AGENTS.md: notes, tests and docs are still needed.",
        "//",
        "// Signal flow (mono), in processing order:",
        "//",
        "//   x: the input",
        ...flow,
        "//",
        `// Latency: ${latency} samples.`,
        "",
        `declare name        "${name}";`,
        `declare description "${description}";`,
        `declare author      "${clean(author)}";`,
        'declare license     "MIT";',
        'declare version     "0.1.0";',
        `declare lv2class    "${lv2class(order)}";`,
        "",
        'import("stdfaust.lib");',
        'pk = library("pedalkit.lib");',
        "",
        ...(fixedConstants.length ? ["// Fixed values.", ...fixedConstants, ""] : []),
        ...(exposedConstants.length ? ["// Controls, in the order they were exposed.", ...exposedConstants, ""] : []),
        "// One named signal per block.",
        "effect(x) = y with {",
        ...lines,
        `    y = ${signal(last)};`,
        "};",
        "",
        "// Reports the oversamplers' delay to the host, which can then compensate it.",
        `latencySamples = ${delays[last] ? delayExpr(delays[last]) : "0"};`,
        "latency = latencySamples",
        '        : hbargraph("Latency [unit:samples] [lv2:reportsLatency] [lv2:integer]", 0, 256);',
        "",
        `process = effect : pk.safety(${SAFETY_CEILING}) : attach(_, latency);`,
        "",
    ].join("\n");

    return { code, latency, controls, warnings };
}
