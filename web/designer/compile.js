// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// Compiling generated code with faustwasm's libfaust. Shared by the page's
// worker (compiler-worker.js) and the Node tests, so both compile the same
// way. The faustwasm classes are passed in, because the page and Node load
// faustwasm from different places.

// Where pedalkit.lib goes in libfaust's in-memory file system.
const LIB_DIR = "/pedalkit";

// -ftz 1 as FAUSTFLAGS in the Makefile, so the browser build flushes
// subnormals the same way as the plugins.
export const COMPILE_ARGS = `-I ${LIB_DIR} -ftz 1`;

// Put pedalkit.lib where the compiler finds it. Call once per compiler.
export function installLibrary(compiler, pedalkitLib) {
    const fs = compiler.fs();
    try {
        fs.mkdirTree(LIB_DIR);
    } catch {
        // Already there.
    }
    fs.writeFile(`${LIB_DIR}/pedalkit.lib`, pedalkitLib);
}

// Compile `code`; returns the factory ({ module, json, ... }) or throws with
// the compiler's message.
export async function compileCode(FaustMonoDspGenerator, compiler, name, code) {
    const generator = new FaustMonoDspGenerator();
    let ok = null;
    let message = "";
    try {
        ok = await generator.compile(compiler, name, code, COMPILE_ARGS);
    } catch (error) {
        message = error.message || String(error);
    }
    if (!ok) throw new Error(compiler.getErrorMessage() || message || "the Faust compiler gave no reason");
    return generator.factory;
}
