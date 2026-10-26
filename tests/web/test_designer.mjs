// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// Effect designer: the code generator in web/designer/, checked on the
// example graphs in tests/web/designer/*.json.
//
// Run with `make web-test` (or `node --test tests/web/test_designer.mjs`
// after `make web`'s npm install). For each example:
//
// * the generated code matches the committed snapshot <name>.dsp, so any
//   change to the generator shows in review (UPDATE_SNAPSHOTS=1 rewrites them)
// * it compiles with faustwasm's libfaust, as the page does
// * the compiled effect reports the latency the generator computed
// * silence in gives silence out
// * the peak stays at or below 0 dBFS on a full-scale input with every
//   exposed control at its maximum, and at its minimum
//
// and for drywet.json, a waveshaper on one path blended 50/50 with the dry
// path: no comb notch, so the generator's latency compensation works. The
// same check on a copy with the compensating delay removed must fail, which
// shows the check would catch a regression.
//
// The native side (system Faust, tools/check-effects.py --dsp-only) runs from
// the Makefile's web-test target.

import assert from "node:assert/strict";
import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import {
    FaustCompiler,
    FaustMonoDspGenerator,
    instantiateFaustModuleFromFile,
    LibFaust,
} from "../../tools/web/node_modules/@grame/faustwasm/dist/esm/index.js";
import { compileCode, installLibrary } from "../../web/designer/compile.js";
import { generate } from "../../web/designer/generate.js";
import { validate } from "../../web/designer/graph.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..", "..");
const EXAMPLES = join(HERE, "designer");
const SR = 48000;
const BLOCK = 128;

// Chosen, as tests/web/test_wasm.py.
const SILENCE_DB = -120;
// Chosen: the generator promises a time-aligned blend, so at 50 % the
// response of drywet.json (in its linear range) must be flat to within this
// across the band. An unaligned 32-sample path notches at 750 Hz by tens of
// dB, far outside it.
const FLAT_DB = 1;
// Chosen: a level where the asymmetric tanh at unity drive is linear to well
// under FLAT_DB, so the response measures the wiring, not the shaper.
const PROBE_DB = -40;
const PROBE_HZ = [50, 100, 200, 400, 750, 1000, 1500, 2250, 3000, 5000, 8000, 10000];

// Fixed author and year, so the snapshots don't change with the calendar.
const OPTIONS = { author: "Joe Heffer", year: 2026 };

const db = (x) => 20 * Math.log10(Math.max(x, 1e-30));
const peak = (y) => y.reduce((m, v) => Math.max(m, Math.abs(v)), 0);
const rms = (y) => Math.sqrt(y.reduce((s, v) => s + v * v, 0) / y.length);
const sine = (hz, seconds, level = 1) =>
    Float32Array.from({ length: Math.round(seconds * SR) }, (_, i) => level * Math.sin((2 * Math.PI * hz * i) / SR));

const faustModule = await instantiateFaustModuleFromFile(
    join(ROOT, "tools", "web", "node_modules", "@grame", "faustwasm", "libfaust-wasm", "libfaust-wasm.js"),
);
const compiler = new FaustCompiler(new LibFaust(faustModule));
installLibrary(compiler, readFileSync(join(ROOT, "src", "lib", "pedalkit.lib"), "utf8"));

async function build(name, code) {
    const t0 = performance.now();
    const factory = await compileCode(FaustMonoDspGenerator, compiler, name, code);
    const ms = performance.now() - t0;
    const meta = JSON.parse(factory.json);
    const addresses = {};
    const walk = (items) => {
        for (const item of items) {
            if (item.items) walk(item.items);
            else addresses[item.label] = item.address;
        }
    };
    walk(meta.ui);
    return { factory, addresses, ms };
}

// Process x after one second of silence (the smoothers settle), with the
// given controls (label -> value). Returns the output and the latency the
// effect reports.
async function render({ factory, addresses }, x, controls = {}) {
    const dsp = await new FaustMonoDspGenerator().createOfflineProcessor(SR, BLOCK, factory);
    dsp.start();
    for (const [label, value] of Object.entries(controls)) dsp.setParamValue(addresses[label], value);
    const inBuf = [new Float32Array(BLOCK)];
    const outBuf = [new Float32Array(BLOCK)];
    for (let n = 0; n < SR; n += BLOCK) dsp.compute(inBuf, outBuf);
    const y = new Float32Array(x.length);
    for (let n = 0; n < x.length; n += BLOCK) {
        const len = Math.min(BLOCK, x.length - n);
        inBuf[0].fill(0);
        inBuf[0].set(x.subarray(n, n + len));
        dsp.compute(inBuf, outBuf);
        y.set(outBuf[0].subarray(0, len), n);
    }
    return { y, latency: dsp.getParamValue(addresses.Latency) };
}

// Gain (dB) at each probe frequency, measured on the second half of a tone.
async function response(effect) {
    const gains = [];
    for (const hz of PROBE_HZ) {
        const x = sine(hz, 0.2, 10 ** (PROBE_DB / 20));
        const { y } = await render(effect, x);
        const half = x.length / 2;
        gains.push(db(rms(y.subarray(half)) / rms(x.subarray(half))));
    }
    return gains;
}

const examples = readdirSync(EXAMPLES)
    .filter((f) => f.endsWith(".json"))
    .map((f) => f.slice(0, -5))
    .sort();

for (const name of examples) {
    test(name, async (t) => {
        const graph = validate(JSON.parse(readFileSync(join(EXAMPLES, `${name}.json`), "utf8")));
        const { code, latency, controls, warnings } = generate(graph, OPTIONS);
        assert.deepEqual(warnings, []);

        await t.test("matches the committed snapshot", () => {
            const path = join(EXAMPLES, `${name}.dsp`);
            if (process.env.UPDATE_SNAPSHOTS) writeFileSync(path, code);
            assert.equal(code, readFileSync(path, "utf8"), `generated code changed; rerun with UPDATE_SNAPSHOTS=1 if intended`);
        });

        const effect = await build(name, code);
        t.diagnostic(`compiled in ${effect.ms.toFixed(0)} ms`);

        await t.test("reports the generator's latency", async () => {
            const { latency: reported } = await render(effect, new Float32Array(BLOCK));
            assert.equal(reported, latency);
        });

        await t.test("silence in gives silence out", async () => {
            const { y } = await render(effect, new Float32Array(SR / 2));
            assert.ok(db(peak(y)) < SILENCE_DB, `peak ${db(peak(y)).toFixed(1)} dB`);
        });

        for (const extreme of ["max", "min"]) {
            await t.test(`peak <= 0 dBFS with every control at its ${extreme}imum`, async () => {
                const settings = Object.fromEntries(controls.map((c) => [c.label, c[extreme]]));
                for (const hz of [41.2, 1000]) {
                    const { y } = await render(effect, sine(hz, 0.5), settings);
                    assert.ok(peak(y) <= 1, `${hz} Hz: peak ${db(peak(y)).toFixed(2)} dBFS`);
                }
            });
        }

        if (name === "drywet") {
            await t.test("no comb notch at a 50 % blend", async () => {
                const gains = await response(effect);
                const spread = Math.max(...gains) - Math.min(...gains);
                assert.ok(spread <= FLAT_DB, `response spread ${spread.toFixed(2)} dB: ${gains.map((g) => g.toFixed(1))}`);
            });

            await t.test("the same check fails without the compensating delay", async () => {
                const broken = code.replace("(x : @(pk.os4Latency))", "x");
                assert.notEqual(broken, code, "the dry path's delay was not found in the generated code");
                const gains = await response(await build(`${name}_uncompensated`, broken));
                assert.ok(Math.max(...gains) - Math.min(...gains) > FLAT_DB);
            });
        }
    });
}
