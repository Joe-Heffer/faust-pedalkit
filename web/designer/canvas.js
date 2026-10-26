// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// The block diagram editor: hand-written SVG with pointer events, so it works
// with a mouse, a pen or a finger and needs no library.
//
//   drag a block          move it
//   drag from an output   (the dot on a block's right) to an input (left) to wire them
//   click a block or wire select it; the page's Delete button or key removes it
//
// All pointer handling sits on the <svg> itself, so redrawing during a drag
// never loses the pointer capture. The editor changes the graph through
// graph.js and tells the page what happened:
//   onSelect(selection)   { block: id } or { wire } or null
//   onChange(kind)        "move" (layout only) or "structure" (needs a recompile)
//   onError(message)      a refused wire

import { BLOCKS } from "./blocks.js";
import { blockById, connect } from "./graph.js";

const NS = "http://www.w3.org/2000/svg";
// Chosen sizes, in SVG units (the viewBox scales them to the screen).
const W = 128; // block width
const H = 56; // block height
const PORT_R = 7; // port radius; the hit area is larger (PORT_HIT)
const PORT_HIT = 16;
const VIEW_W = 1280; // viewBox, wide enough for a dozen blocks in a row
const VIEW_H = 480;

function el(name, attrs = {}, parent = null) {
    const node = document.createElementNS(NS, name);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    if (parent) parent.append(node);
    return node;
}

const inPort = (block, port) => {
    const n = BLOCKS[block.type].inputs.length;
    return { x: block.x, y: block.y + (H * (port + 1)) / (n + 1) };
};
const outPort = (block) => ({ x: block.x + W, y: block.y + H / 2 });

function wirePath(a, b) {
    const dx = Math.max(40, Math.abs(b.x - a.x) / 2);
    return `M ${a.x} ${a.y} C ${a.x + dx} ${a.y}, ${b.x - dx} ${b.y}, ${b.x} ${b.y}`;
}

// Short text under a block's title: its variant, or what it does.
function subtitle(block) {
    const def = BLOCKS[block.type];
    if (def.variants) return def.variants[block.variant].label;
    return block.title === def.label ? "" : def.label;
}

export function createCanvas(svg, getGraph, { onSelect, onChange, onError }) {
    svg.setAttribute("viewBox", `0 0 ${VIEW_W} ${VIEW_H}`);
    svg.setAttribute("role", "application");
    svg.setAttribute("aria-label", "Block diagram");
    svg.tabIndex = 0;
    let selection = null;
    let drag = null; // { kind: "move", id, dx, dy, moved } or { kind: "wire", from, to: {x, y} }

    const toSvg = (event) => {
        const p = new DOMPoint(event.clientX, event.clientY).matrixTransform(svg.getScreenCTM().inverse());
        return { x: p.x, y: p.y };
    };
    const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

    function render() {
        const graph = getGraph();
        svg.replaceChildren();
        const wires = el("g", { class: "wires" }, svg);
        for (const w of graph.wires) {
            const a = outPort(blockById(graph, w.from));
            const b = inPort(blockById(graph, w.to), w.port);
            const d = wirePath(a, b);
            const selected = selection?.wire && selection.wire.from === w.from && selection.wire.to === w.to && selection.wire.port === w.port;
            const g = el("g", { class: `wire${selected ? " selected" : ""}`, "data-wire": JSON.stringify(w) }, wires);
            el("path", { d, class: "wire-hit" }, g);
            el("path", { d, class: "wire-line" }, g);
        }
        if (drag?.kind === "wire") {
            const a = outPort(blockById(graph, drag.from));
            el("path", { d: wirePath(a, drag.to), class: "wire-line pending" }, wires);
        }

        for (const block of graph.blocks) {
            const def = BLOCKS[block.type];
            const g = el(
                "g",
                {
                    class: `block block-${block.type}${selection?.block === block.id ? " selected" : ""}`,
                    transform: `translate(${block.x} ${block.y})`,
                    "data-block": block.id,
                },
                svg,
            );
            el("rect", { width: W, height: H, rx: 8 }, g);
            el("text", { x: W / 2, y: 23, class: "title" }, g).textContent = block.title;
            const sub = subtitle(block);
            if (sub) el("text", { x: W / 2, y: 41, class: "subtitle" }, g).textContent = sub;
            def.inputs.forEach((label, port) => {
                const p = inPort(block, port);
                const pg = el("g", { class: "port in", "data-in": `${block.id}:${port}` }, g);
                el("circle", { cx: p.x - block.x, cy: p.y - block.y, r: PORT_HIT, class: "port-hit" }, pg);
                el("circle", { cx: p.x - block.x, cy: p.y - block.y, r: PORT_R }, pg);
                if (def.inputs.length > 1) el("text", { x: 14, y: p.y - block.y + 4, class: "port-label" }, g).textContent = label;
            });
            if (def.outputs) {
                const p = outPort(block);
                const pg = el("g", { class: "port out", "data-out": block.id }, g);
                el("circle", { cx: p.x - block.x, cy: p.y - block.y, r: PORT_HIT, class: "port-hit" }, pg);
                el("circle", { cx: p.x - block.x, cy: p.y - block.y, r: PORT_R }, pg);
            }
        }
    }

    function select(next) {
        selection = next;
        render();
        onSelect(selection);
    }

    svg.addEventListener("pointerdown", (event) => {
        const graph = getGraph();
        const target = event.target.closest("[data-out], [data-in], [data-block], [data-wire]");
        const p = toSvg(event);
        if (target?.dataset.out) {
            drag = { kind: "wire", from: target.dataset.out, to: p };
        } else if (target?.dataset.in) {
            // Dragging from a wired input picks the wire up again.
            const [id, port] = target.dataset.in.split(":");
            const wire = graph.wires.find((w) => w.to === id && w.port === Number(port));
            if (!wire) return;
            graph.wires = graph.wires.filter((w) => w !== wire);
            drag = { kind: "wire", from: wire.from, to: p, lifted: true };
        } else if (target?.dataset.block) {
            const block = blockById(graph, target.dataset.block);
            drag = { kind: "move", id: block.id, dx: p.x - block.x, dy: p.y - block.y, moved: false };
            select({ block: block.id });
        } else if (target?.dataset.wire) {
            select({ wire: JSON.parse(target.dataset.wire) });
            return;
        } else {
            select(null);
            return;
        }
        svg.setPointerCapture(event.pointerId);
        event.preventDefault();
        render();
    });

    svg.addEventListener("pointermove", (event) => {
        if (!drag) return;
        const p = toSvg(event);
        if (drag.kind === "move") {
            const block = blockById(getGraph(), drag.id);
            block.x = Math.round(clamp(p.x - drag.dx, 0, VIEW_W - W));
            block.y = Math.round(clamp(p.y - drag.dy, 0, VIEW_H - H));
            drag.moved = true;
        } else {
            drag.to = p;
        }
        render();
    });

    const finish = (event) => {
        if (!drag) return;
        const done = drag;
        drag = null;
        if (done.kind === "move") {
            render();
            if (done.moved) onChange("move");
            return;
        }
        // Released over an input? The capture means event.target is the svg,
        // so look underneath the pointer.
        const under = document.elementFromPoint(event.clientX, event.clientY)?.closest("[data-in]");
        if (under && event.type === "pointerup") {
            const [id, port] = under.dataset.in.split(":");
            const problem = connect(getGraph(), done.from, id, Number(port));
            if (problem) onError(problem);
        }
        render();
        if (under || done.lifted) onChange("structure");
    };
    svg.addEventListener("pointerup", finish);
    svg.addEventListener("pointercancel", finish);

    render();
    return {
        render,
        select,
        get selection() {
            return selection;
        },
        // Where to put a new block: the next free spot along the middle row.
        freeSpot() {
            const graph = getGraph();
            for (let y = VIEW_H / 2 - H / 2; y < VIEW_H - H; y += H + 24) {
                for (let x = 180; x < VIEW_W - W - 160; x += W + 32) {
                    if (!graph.blocks.some((b) => Math.abs(b.x - x) < W && Math.abs(b.y - y) < H)) return { x, y };
                }
            }
            return { x: 180, y: 20 };
        },
    };
}
