// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// Synthesised test riffs, shared by the demo and the designer, so both pages
// make a sound with no file and no committed audio.

import { dbToGain } from "./controls.js";

// Chosen values (see docs/usage/browser.md).
const RIFF_PEAK_DB = -10; // test riff peak level, a typical bass DI peak
const RIFF_ROOT_HZ = 41.2034; // low E on a four-string bass (E1)
// Original riffs, chosen to show different sides of a bass effect. Notes are
// semitones above the root, one per step (null is a rest), and a step is an
// eighth note at `bpm`. `decay` scales how fast the pluck dies away (1 is a
// plucked string; lower rings on, like a sustained note) and `sub` mixes in a
// sine an octave below, for a synth-bass weight. All values are chosen.
export const RIFFS = {
    root: {
        label: "Root and octave (E)",
        bpm: 100,
        decay: 1,
        sub: 0,
        // Open E and the octave, where bass drive matters most.
        notes: [0, 0, 12, 0, 3, 0, 5, 7, 0, 0, 12, 0, 10, 7, 5, 3],
    },
    walking: {
        label: "Walking line (A minor)",
        bpm: 120,
        decay: 0.8,
        sub: 0,
        // Quarter-note walk through A minor: A C D E G E D C (A is 5 semitones up).
        notes: [5, null, 8, null, 10, null, 12, null, 15, null, 12, null, 10, null, 8, null],
    },
    octaves: {
        label: "Octave pulse (disco)",
        bpm: 116,
        decay: 1.2,
        sub: 0,
        // Offbeat octave jumps on a pedal E, with a dropped note in the last bar.
        notes: [0, 12, 0, 12, 0, 12, 0, 12, 3, 15, 3, 15, 5, 17, 7, null],
    },
    sustained: {
        label: "Slow sustained notes",
        bpm: 70,
        decay: 0.15,
        sub: 0,
        // Long held notes expose compression, sustain and low-end tracking.
        notes: [0, null, null, null, 7, null, null, null, 5, null, null, null, 3, null, null, null],
    },
    synth: {
        label: "Synth bass (sub octave)",
        bpm: 105,
        decay: 0.35,
        sub: 0.8,
        // Syncopated 16th-note line an octave up, with a sine sub under each note.
        notes: [12, null, 12, 12, null, 15, null, 12, 17, null, 12, null, 10, null, 12, 7],
        step16: true,
    },
    slap: {
        label: "Funk slap (staccato)",
        bpm: 98,
        decay: 3,
        sub: 0,
        // Short bright notes with gaps: heavy on attack transients.
        notes: [0, null, 12, 0, null, 0, 12, null, 3, null, 5, 5, null, 7, 12, null],
        step16: true,
    },
};

// Synthesised bass riffs, so the demo makes a sound with no file and no
// committed audio. Each note is a sum of harmonics at 1/k amplitude (a
// sawtooth-like pluck) whose upper harmonics die away faster, roughly as a
// plucked string's do. A riff may also add a sine an octave below.
export function makeRiff(sampleRate, riff) {
    const step = (60 / riff.bpm / 2) / (riff.step16 ? 2 : 1);
    const noteLen = Math.round(step * sampleRate);
    const buffer = new AudioBuffer({ length: noteLen * riff.notes.length, sampleRate, numberOfChannels: 1 });
    const y = buffer.getChannelData(0);
    const attack = Math.round(0.002 * sampleRate);
    const release = Math.round(0.02 * sampleRate);
    riff.notes.forEach((semitones, n) => {
        if (semitones === null) return;
        const f = RIFF_ROOT_HZ * 2 ** (semitones / 12);
        const offset = n * noteLen;
        // A note rings through the rests that follow it.
        let steps = 1;
        while (n + steps < riff.notes.length && riff.notes[n + steps] === null) steps++;
        const len = steps * noteLen;
        const note = new Float32Array(len);
        for (let k = 1; k * f < 5000; k++) {
            const w = (2 * Math.PI * k * f) / sampleRate;
            const decay = Math.exp((-(2 + 0.8 * k) * riff.decay) / sampleRate);
            let amp = 1 / k;
            for (let i = 0; i < len; i++) {
                note[i] += amp * Math.sin(w * i);
                amp *= decay;
            }
        }
        if (riff.sub) {
            const w = (2 * Math.PI * f) / (2 * sampleRate);
            const decay = Math.exp((-2 * riff.decay) / sampleRate);
            let amp = riff.sub;
            for (let i = 0; i < len; i++) {
                note[i] += amp * Math.sin(w * i);
                amp *= decay;
            }
        }
        for (let i = 0; i < attack; i++) note[i] *= i / attack;
        for (let i = 0; i < release; i++) note[len - 1 - i] *= i / release;
        for (let i = 0; i < len; i++) y[offset + i] += note[i];
    });
    let peak = 0;
    for (const v of y) peak = Math.max(peak, Math.abs(v));
    const scale = dbToGain(RIFF_PEAK_DB) / peak;
    for (let i = 0; i < y.length; i++) y[i] *= scale;
    return buffer;
}
