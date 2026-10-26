// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// The designer's palette: one entry per block type. Adding a block is a new
// entry here; generate.js and the page read nothing else.
//
// An entry has:
//   label        name in the palette
//   inputs       input port labels ([] for none)
//   outputs      number of output ports (0 or 1)
//   params       parameters shared by every variant
//   variants     optional { key: { label, params, faust } }; a block without
//                variants has its own `faust`
//   oversampled  true if `faust` wraps its work in pk.oversample4, which adds
//                pk.os4Latency samples of delay
//   faust(p, ins) Faust expression for the block's output, given `p` (each
//                parameter's Faust name, already in the unit the template
//                expects) and `ins` (each input's signal expression)
//
// A parameter has a key, label, unit (always dB, Hz, % or oct, so every
// exposed control carries one), min, max, step, init, a tooltip, optional
// `log` (a log-scale control) and `to`, which turns the control's value into
// the value the Faust function takes. Every range and default is chosen in
// the designer; docs/usage/designer.md says why.

const db2lin = (x) => `ba.db2linear(${x})`;
const pct = (x) => `(${x} / 100)`;

const drive = {
    key: "drive",
    label: "Drive",
    unit: "dB",
    min: 0,
    max: 40,
    step: 0.1,
    init: 12,
    tooltip: "Gain into the shaper",
};
const ceiling = (key, label, tooltip) => ({
    key,
    label,
    unit: "dB",
    min: -24,
    max: 0,
    step: 0.1,
    init: -3,
    tooltip,
    to: db2lin,
});
// Knee hardness: 0 % is the softest knee (n = 1) and 100 % a near-hard clip
// (n = 10), the range where pk.kneeClip changes audibly.
const hardness = {
    key: "hardness",
    label: "Hardness",
    unit: "%",
    min: 0,
    max: 100,
    step: 1,
    init: 30,
    tooltip: "0 = soft knee, 100 = hard clip",
    to: (x) => `(1 + 9 * (${x}) / 100)`,
};
const freq = {
    key: "freq",
    label: "Frequency",
    unit: "Hz",
    min: 20,
    max: 20000,
    step: 1,
    init: 1000,
    log: true,
    tooltip: "Corner or centre frequency",
};

// The drive gain goes inside the oversampler with the shaper, so the shaper
// sees the boosted signal at the 4x rate and the function stays memoryless.
const shaper = (p, ins, fn) => `${ins[0]} : pk.oversample4(*(${db2lin(p.drive)}) : ${fn})`;

export const BLOCKS = {
    input: { label: "Input", inputs: [], outputs: 1, params: [], fixed: true },
    output: { label: "Output", inputs: ["In"], outputs: 0, params: [], fixed: true },
    gain: {
        label: "Gain",
        inputs: ["In"],
        outputs: 1,
        params: [{ key: "gain", label: "Gain", unit: "dB", min: -24, max: 24, step: 0.1, init: 0, tooltip: "Level change" }],
        faust: (p, ins) => `${ins[0]} : *(${db2lin(p.gain)})`,
    },
    waveshaper: {
        label: "Waveshaper",
        inputs: ["In"],
        outputs: 1,
        oversampled: true,
        params: [drive],
        variants: {
            soft: {
                label: "Soft (symmetric tanh)",
                params: [ceiling("ceiling", "Ceiling", "Level the output approaches")],
                faust: (p, ins) => shaper(p, ins, `pk.softSat(${p.ceiling})`),
            },
            asym: {
                label: "Asymmetric tanh",
                params: [
                    ceiling("pos", "Positive ceiling", "Level positive peaks approach"),
                    { ...ceiling("neg", "Negative ceiling", "Level negative peaks approach"), init: -6 },
                ],
                faust: (p, ins) => shaper(p, ins, `pk.asymTanh(${p.pos}, ${p.neg})`),
            },
            knee: {
                label: "Knee clipper",
                params: [ceiling("ceiling", "Ceiling", "Level the output limits at"), hardness],
                faust: (p, ins) => shaper(p, ins, `pk.kneeClip(${p.ceiling}, ${p.hardness})`),
            },
            softhard: {
                label: "Soft above, hard below",
                params: [
                    ceiling("pos", "Positive ceiling", "Level positive peaks approach"),
                    { ...ceiling("neg", "Negative ceiling", "Level negative peaks limit at"), init: -6 },
                    hardness,
                ],
                faust: (p, ins) => shaper(p, ins, `pk.asymSoftHard(${p.pos}, ${p.neg}, ${p.hardness})`),
            },
        },
    },
    filter: {
        label: "Filter",
        inputs: ["In"],
        outputs: 1,
        params: [freq],
        variants: {
            lp1: { label: "Low-pass, 1st order", params: [], faust: (p, ins) => `${ins[0]} : fi.lowpass(1, ${p.freq})` },
            lp2: { label: "Low-pass, 2nd order", params: [], faust: (p, ins) => `${ins[0]} : fi.lowpass(2, ${p.freq})` },
            hp1: { label: "High-pass, 1st order", params: [], faust: (p, ins) => `${ins[0]} : fi.highpass(1, ${p.freq})` },
            hp2: { label: "High-pass, 2nd order", params: [], faust: (p, ins) => `${ins[0]} : fi.highpass(2, ${p.freq})` },
            peak: {
                label: "Peaking EQ",
                params: [
                    { key: "gain", label: "Gain", unit: "dB", min: -18, max: 18, step: 0.1, init: 6, tooltip: "Boost or cut at the centre" },
                    {
                        key: "width",
                        label: "Width",
                        unit: "oct",
                        min: 0.1,
                        max: 4,
                        step: 0.01,
                        init: 1,
                        tooltip: "Bandwidth in octaves",
                        // Q of a band `x` octaves wide: sqrt(2^x) / (2^x - 1).
                        to: (x) => `(sqrt(2 ^ (${x})) / (2 ^ (${x}) - 1))`,
                    },
                ],
                faust: (p, ins) => `${ins[0]} : fi.peak_eq_cq(${p.gain}, ${p.freq}, ${p.width})`,
            },
        },
    },
    dcblock: {
        label: "DC blocker",
        inputs: ["In"],
        outputs: 1,
        params: [],
        // 5 Hz rather than fi.dcblocker's ~35 Hz, so it keeps a bass's low E.
        faust: (p, ins) => `${ins[0]} : fi.dcblockerat(5)`,
    },
    mix: {
        label: "Mix",
        inputs: ["A", "B"],
        outputs: 1,
        params: [
            {
                key: "balance",
                label: "Balance",
                unit: "%",
                min: 0,
                max: 100,
                step: 0.1,
                init: 50,
                tooltip: "0 = A only, 100 = B only",
                to: pct,
            },
        ],
        faust: (p, ins) => `${ins[0]} * (1 - ${p.balance}) + ${ins[1]} * ${p.balance}`,
    },
};

// Block types offered in the palette, in order.
export const PALETTE = ["gain", "waveshaper", "filter", "dcblock", "mix"];

// The parameters of a block in its current variant.
export function paramsOf(block) {
    const def = BLOCKS[block.type];
    const variant = def.variants?.[block.variant];
    return [...def.params, ...(variant?.params || [])];
}

export function templateOf(block) {
    const def = BLOCKS[block.type];
    return def.variants ? def.variants[block.variant].faust : def.faust;
}

export function defaultVariant(type) {
    const variants = BLOCKS[type].variants;
    return variants ? Object.keys(variants)[0] : undefined;
}
