// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// Controls built from a Faust effect's dsp-meta.json, shared by the demo and
// the designer.

export const dbToGain = (db) => 10 ** (db / 20);
export const metaValue = (meta, key) => (meta.meta || []).map((m) => m[key]).find((v) => v !== undefined);
export const itemMeta = (item, key) => (item.meta || []).map((m) => m[key]).find((v) => v !== undefined);

// Positions on a log-scale slider ([scale:log], e.g. a frequency), chosen
// fine enough that one step is under 1 % across 20 Hz to 20 kHz.
const LOG_STEPS = 1000;

export function formatValue(value, item) {
    const step = item.step || 1;
    const decimals = Math.max(0, Math.min(3, -Math.floor(Math.log10(step))));
    const unit = itemMeta(item, "unit");
    const number = value.toFixed(decimals).replace("-", "−");
    return unit ? `${number} ${unit}` : number;
}

// Flatten the Faust UI tree into its controls, in declaration order (Faust
// has already sorted them by their [n] prefixes).
export function flatten(items, out = []) {
    for (const item of items) {
        if (item.items) flatten(item.items, out);
        else out.push(item);
    }
    return out;
}

// A range input for `item` (an hslider, vslider or nentry), mapped through
// a log scale when the control asks for one. Returns { input, get, set }.
export function rangeInput(item) {
    const input = document.createElement("input");
    input.type = "range";
    const log = itemMeta(item, "scale") === "log" && item.min > 0;
    if (log) {
        input.min = 0;
        input.max = LOG_STEPS;
        input.step = 1;
    } else {
        input.min = item.min;
        input.max = item.max;
        input.step = item.step;
    }
    const get = () => {
        if (!log) return Number(input.value);
        const v = item.min * (item.max / item.min) ** (Number(input.value) / LOG_STEPS);
        return Math.min(item.max, Math.max(item.min, Math.round(v / item.step) * item.step));
    };
    const set = (value) => {
        input.value = log ? (LOG_STEPS * Math.log(value / item.min)) / Math.log(item.max / item.min) : value;
    };
    set(item.init);
    return { input, get, set };
}

// Build the controls for `meta` into `controlsEl` (inputs) and `readoutsEl`
// (a <dl> for bargraphs). `setParam(address, value)` is called on every
// change and once per control with its starting value, which is `initial`'s
// value for that address if it has one. Returns { readouts, latencyAddress,
// reset }, where readouts maps a bargraph's address to { item, dd }.
export function buildControls(meta, controlsEl, readoutsEl, setParam, initial = {}) {
    controlsEl.replaceChildren();
    readoutsEl.replaceChildren();
    const readouts = {};
    const resets = [];
    let latencyAddress = null;

    for (const item of flatten(meta.ui)) {
        const id = `ctl-${item.address.replace(/[^A-Za-z0-9]/g, "-")}`;
        const tooltip = itemMeta(item, "tooltip");

        if (item.type === "hbargraph" || item.type === "vbargraph") {
            const dt = document.createElement("dt");
            dt.textContent = item.label;
            const dd = document.createElement("dd");
            dd.textContent = "–";
            readoutsEl.append(dt, dd);
            readouts[item.address] = { item, dd };
            if ((item.meta || []).some((m) => m.lv2 === "reportsLatency")) latencyAddress = item.address;
            continue;
        }

        const wrap = document.createElement("div");
        wrap.className = "control";
        const label = document.createElement("label");
        label.htmlFor = id;
        let input;

        if (item.type === "checkbox" || item.type === "button") {
            wrap.classList.add("checkbox");
            input = document.createElement("input");
            input.type = "checkbox";
            input.checked = Boolean(initial[item.address]);
            label.append(input, ` ${item.label}`);
            setParam(item.address, input.checked ? 1 : 0);
            input.addEventListener("change", () => setParam(item.address, input.checked ? 1 : 0));
            resets.push(() => {
                input.checked = false;
                setParam(item.address, 0);
            });
            wrap.append(label);
        } else {
            // hslider, vslider and nentry all become a horizontal range input.
            const range = rangeInput(item);
            input = range.input;
            const output = document.createElement("output");
            output.htmlFor = id;
            const show = () => {
                output.textContent = formatValue(range.get(), item);
                input.setAttribute("aria-valuetext", output.textContent);
            };
            range.set(initial[item.address] ?? item.init);
            show();
            setParam(item.address, range.get());
            input.addEventListener("input", () => {
                show();
                setParam(item.address, range.get());
            });
            resets.push(() => {
                range.set(item.init);
                show();
                setParam(item.address, item.init);
            });
            label.append(item.label, output);
            wrap.append(label, input);
        }
        input.id = id;

        if (tooltip) {
            const hint = document.createElement("div");
            hint.className = "hint";
            hint.id = `${id}-hint`;
            hint.textContent = tooltip;
            input.setAttribute("aria-describedby", hint.id);
            wrap.append(hint);
        }
        controlsEl.append(wrap);
    }
    return { readouts, latencyAddress, reset: () => resets.forEach((r) => r()) };
}
