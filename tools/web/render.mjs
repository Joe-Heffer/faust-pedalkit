#!/usr/bin/env node
// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// Offline renderer for the browser build (the WebAssembly that `make web`
// writes to build/web/<name>/), so tests/web/ can compare it with the native
// renderer and time it.
//
// Usage: render.mjs <dir> <samplerate> [Label=value ...] < in.f32 > out.f32
//
// Same contract as tests/lib/render-arch.cpp: reads mono 32-bit float
// samples from stdin, runs two seconds of silence first so the smoothers
// settle, and writes the processed samples to stdout. It also prints one line
// to stderr, `realtime <factor>`: seconds of audio processed per second of
// compute, for the input after the pre-roll.

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { FaustMonoDspGenerator } from "@grame/faustwasm/dist/esm/index.js";

// 128 frames is the AudioWorklet render quantum, so this times the DSP in
// blocks of the size the browser gives it.
const BLOCK = 128;

const [dir, srArg, ...params] = process.argv.slice(2);
if (!dir || !srArg) {
    process.stderr.write("usage: render.mjs <dir> <samplerate> [Label=value ...]\n");
    process.exit(2);
}
const sr = Number(srArg);
const json = readFileSync(join(dir, "dsp-meta.json"), "utf8");
const module = await WebAssembly.compile(readFileSync(join(dir, "dsp-module.wasm")));

const generator = new FaustMonoDspGenerator();
const dsp = await generator.createOfflineProcessor(sr, BLOCK, { module, json, soundfiles: {} });
dsp.start();

// Address controls by label, as the native renderer does.
const addresses = {};
const walk = (items) => {
    for (const item of items) {
        if (item.items) walk(item.items);
        else if (item.address) addresses[item.label] = item.address;
    }
};
walk(JSON.parse(json).ui);
for (const arg of params) {
    const eq = arg.indexOf("=");
    const label = arg.slice(0, eq);
    if (eq < 0 || !(label in addresses)) {
        process.stderr.write(`unknown parameter '${arg}'\n`);
        process.exit(2);
    }
    dsp.setParamValue(addresses[label], Number(arg.slice(eq + 1)));
}

const input = new Float32Array(new Uint8Array(readFileSync(0)).buffer);
const inBuf = [new Float32Array(BLOCK)];
const outBuf = [new Float32Array(BLOCK)];

for (let n = 0; n < 2 * sr; n += BLOCK) dsp.compute(inBuf, outBuf);

const output = new Float32Array(input.length);
const t0 = process.hrtime.bigint();
for (let n = 0; n < input.length; n += BLOCK) {
    const len = Math.min(BLOCK, input.length - n);
    inBuf[0].fill(0);
    inBuf[0].set(input.subarray(n, n + len));
    dsp.compute(inBuf, outBuf);
    output.set(outBuf[0].subarray(0, len), n);
}
const seconds = Number(process.hrtime.bigint() - t0) / 1e9;
process.stderr.write(`realtime ${(input.length / sr / Math.max(seconds, 1e-9)).toFixed(1)}\n`);
process.stdout.write(Buffer.from(output.buffer));
