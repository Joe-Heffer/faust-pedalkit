// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// The designer's document: a graph of blocks and wires, kept as plain JSON so
// it can be saved, exported and imported as it is.
//
//   {
//     format: 1,
//     name: "My Effect",
//     description: "...",
//     author: "...",           (optional; the SPDX and declare lines)
//     blocks: [{ id, type, variant, title, x, y,
//                params: { <key>: { value, exposed } } }],
//     wires: [{ from: <block id>, to: <block id>, port: <input index> }],
//   }
//
// Block ids double as Faust identifiers in the generated code, so they are
// the type plus a number (gain1, waveshaper2). The Input and Output blocks
// are always there, with the ids "input" and "output".
//
// The functions here change the graph in place and never touch the DOM, so
// the page and the Node tests share them.

import { BLOCKS, defaultVariant, paramsOf } from "./blocks.js";

export const FORMAT = 1;

export function newGraph(name = "My Effect") {
    return {
        format: FORMAT,
        name,
        description: "Designed in the Pedal Kit effect designer",
        author: "",
        blocks: [
            { id: "input", type: "input", title: "Input", x: 16, y: 212, params: {} },
            { id: "output", type: "output", title: "Output", x: 1136, y: 212, params: {} },
        ],
        // Wired straight through, so a new design plays the dry signal.
        wires: [{ from: "input", to: "output", port: 0 }],
    };
}

export const blockById = (graph, id) => graph.blocks.find((b) => b.id === id);

// Make sure the block has a value for every parameter of its variant, keeping
// the ones it already has.
export function fillParams(block) {
    for (const p of paramsOf(block)) block.params[p.key] ??= { value: p.init, exposed: false };
    return block;
}

export function addBlock(graph, type, x, y) {
    const def = BLOCKS[type];
    if (!def || def.fixed) throw new Error(`unknown block type '${type}'`);
    let n = 1;
    while (blockById(graph, `${type}${n}`)) n++;
    const block = fillParams({ id: `${type}${n}`, type, variant: defaultVariant(type), title: `${def.label} ${n}`, x, y, params: {} });
    graph.blocks.push(block);
    return block;
}

export function removeBlock(graph, id) {
    const block = blockById(graph, id);
    if (!block || BLOCKS[block.type].fixed) return false;
    graph.blocks = graph.blocks.filter((b) => b !== block);
    graph.wires = graph.wires.filter((w) => w.from !== id && w.to !== id);
    return true;
}

export function setVariant(block, variant) {
    block.variant = variant;
    fillParams(block);
}

// True if `to` can already reach `from` along wires, so a wire from -> to
// would close a loop.
function reaches(graph, start, target) {
    const seen = new Set();
    const stack = [start];
    while (stack.length) {
        const id = stack.pop();
        if (id === target) return true;
        if (seen.has(id)) continue;
        seen.add(id);
        for (const w of graph.wires) if (w.from === id) stack.push(w.to);
    }
    return false;
}

// Connect `from`'s output to input `port` of `to`. An input takes one wire,
// so a new wire replaces the old one; an output may feed any number of
// inputs. Returns null on success, or the reason the wire was refused.
export function connect(graph, from, to, port = 0) {
    const src = blockById(graph, from);
    const dst = blockById(graph, to);
    if (!src || !dst) return "no such block";
    if (BLOCKS[src.type].outputs < 1) return `${src.title} has no output`;
    if (port >= BLOCKS[dst.type].inputs.length) return `${dst.title} has no input ${port + 1}`;
    if (from === to || reaches(graph, to, from)) return "that wire would make a feedback loop, which the designer does not support";
    graph.wires = graph.wires.filter((w) => !(w.to === to && w.port === port));
    graph.wires.push({ from, to, port });
    return null;
}

export function disconnect(graph, wire) {
    graph.wires = graph.wires.filter((w) => !(w.from === wire.from && w.to === wire.to && w.port === wire.port));
}

// The blocks that feed Output, directly or not, in an order where every block
// comes after the blocks that feed it. Blocks that don't reach Output make no
// sound, so they are left out.
export function processingOrder(graph) {
    const needed = new Set();
    const stack = ["output"];
    while (stack.length) {
        const id = stack.pop();
        if (needed.has(id)) continue;
        needed.add(id);
        for (const w of graph.wires) if (w.to === id) stack.push(w.from);
    }
    const order = [];
    const done = new Set();
    const visit = (id) => {
        if (done.has(id)) return;
        done.add(id);
        for (const w of graph.wires) if (w.to === id) visit(w.from);
        order.push(blockById(graph, id));
    };
    // Visit in the graph's own block order, so the output is stable.
    for (const b of graph.blocks) if (needed.has(b.id)) visit(b.id);
    return order;
}

// The wire into input `port` of block `id`, if any.
export const wireInto = (graph, id, port) => graph.wires.find((w) => w.to === id && w.port === port);

// Check a graph loaded from a file or localStorage enough that the page and
// generator can trust it. Throws with a readable message.
export function validate(graph) {
    if (!graph || graph.format !== FORMAT) throw new Error(`not a designer graph (format ${FORMAT})`);
    if (!Array.isArray(graph.blocks) || !Array.isArray(graph.wires)) throw new Error("graph has no blocks or wires");
    const ids = new Set();
    for (const b of graph.blocks) {
        if (!BLOCKS[b.type]) throw new Error(`unknown block type '${b.type}'`);
        if (!/^[a-z][a-z0-9]*$/.test(b.id) || ids.has(b.id)) throw new Error(`bad or repeated block id '${b.id}'`);
        if (BLOCKS[b.type].variants && !BLOCKS[b.type].variants[b.variant]) throw new Error(`${b.id}: unknown variant '${b.variant}'`);
        ids.add(b.id);
        b.params ??= {};
        fillParams(b);
    }
    if (!ids.has("input") || !ids.has("output")) throw new Error("graph has no Input or Output");
    const wires = graph.wires;
    graph.wires = [];
    for (const w of wires) {
        const problem = connect(graph, w.from, w.to, w.port);
        if (problem) throw new Error(`wire ${w.from} -> ${w.to}: ${problem}`);
    }
    return graph;
}
