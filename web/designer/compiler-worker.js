// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// The Faust compiler, in a module worker so that compiling (a few hundred
// milliseconds per waveshaper) never stalls the page.
//
// libfaust (about 3.5 MB of WebAssembly and 2.3 MB of Faust libraries) loads
// on the first request only. faustwasm's instantiateFaustModuleFromFile
// takes its Node branch outside a window, so this does the browser half of
// it here: fetch the emscripten script, import it from a blob URL and hand
// it the binaries.
//
// Messages in:  { id, name, code }
// Messages out: { id, module, json, ms } (a WebAssembly.Module and the
//               effect's dsp-meta JSON) or { id, error }

import { FaustCompiler, FaustMonoDspGenerator, LibFaust } from "../faustwasm/index.js";
import { compileCode, installLibrary } from "./compile.js";

const LIBFAUST = new URL("libfaust/libfaust-wasm.js", import.meta.url);
const PEDALKIT = new URL("pedalkit.lib", import.meta.url);

async function fetchOk(url, as) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`${url.pathname}: HTTP ${response.status}`);
    return response[as]();
}

async function loadCompiler() {
    const [script, data, wasm, pedalkit] = await Promise.all([
        fetchOk(LIBFAUST, "text"),
        fetchOk(new URL("libfaust-wasm.data", LIBFAUST), "arrayBuffer"),
        fetchOk(new URL("libfaust-wasm.wasm", LIBFAUST), "arrayBuffer"),
        fetchOk(PEDALKIT, "text"),
    ]);
    const factoryName = script.match(/var (\w+)\s*=\s*\(/)?.[1];
    if (!factoryName) throw new Error("libfaust-wasm.js: no module factory found");
    const blob = new Blob([`${script}\nexport default ${factoryName};\n`], { type: "text/javascript" });
    const url = URL.createObjectURL(blob);
    let FaustModule;
    try {
        FaustModule = (await import(url)).default;
    } finally {
        URL.revokeObjectURL(url);
    }
    const faustModule = await FaustModule({
        wasmBinary: wasm,
        getPreloadedPackage: (name) => (name === "libfaust-wasm.data" ? data : new ArrayBuffer(0)),
    });
    const compiler = new FaustCompiler(new LibFaust(faustModule));
    installLibrary(compiler, pedalkit);
    return compiler;
}

let compiler = null;

self.onmessage = async ({ data: { id, name, code } }) => {
    try {
        compiler ??= loadCompiler();
        const ready = await compiler;
        const t0 = performance.now();
        const factory = await compileCode(FaustMonoDspGenerator, ready, name, code);
        self.postMessage({ id, module: factory.module, json: factory.json, ms: performance.now() - t0 });
    } catch (error) {
        // A failed load is retried on the next request.
        if (!(await Promise.resolve(compiler).catch(() => null))) compiler = null;
        self.postMessage({ id, error: error.message || String(error) });
    }
};
