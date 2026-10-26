# Designing new sounds

Faust Pedal Kit exists to make effects that don't exist yet. Modelling classic hardware is part of the work, but as a means rather than the goal: a good model teaches how a circuit gets its character, calibrates the measurement tools against something known, and leaves behind building blocks that new designs can reuse, bend and recombine.

This page covers the creative side of adding an effect. The mechanics (DSP conventions, tests, build and docs) are in [Adding an effect](adding-an-effect.md).

## Three kinds of effect

| Kind | Starts from | Notes | Example |
|---|---|---|---|
| **Original** | A sonic idea, with no single reference device | `docs/<name>/design-notes.md` | None yet: this is where new effects should go |
| **Circuit-inspired** | A real circuit, deliberately taken somewhere it couldn't go | Design notes, plus circuit notes for the borrowed part | [MidHump](../midhump/index.md) |
| **Modelled** | One piece of hardware, measured and sourced | `docs/<name>/circuit-notes.md` | [BassDrive](../bassdrive/index.md), [BassPreamp](../basspreamp/index.md) |

Prefer the first two. When you do build a model, say what it makes possible that the hardware does not, and move what is reusable into the [shared library](pedalkit-lib.md).

## Ways in

Some directions that suit Faust and the tools here. They are prompts, not a roadmap.

- **Break the physics.** Take a modelled stage and give it values no component could have: a clipper whose asymmetry follows the input envelope, a tone stack whose corner frequencies track pitch, a bias that drifts with playing dynamics.
- **Recombine.** Put blocks that never share a box in one signal path: a speaker voicing inside a feedback loop, a blend that crossfades between two different drive characters, a filter between two oversampled clippers.
- **Split and treat.** Divide the signal by frequency, by envelope or by harmonic content, and process each part differently: clean lows with folded highs, transient-only fuzz, distortion that only acts on sustain.
- **Make the control the instrument.** Design around one expressive control that moves several parameters along a path chosen by ear, instead of a row of independent knobs.
- **Start from a measurement.** Pick a target you can plot, such as a harmonic profile, an intermodulation pattern or a response that changes with level, and work backwards to a structure that produces it.

## Writing design notes

`docs/<name>/design-notes.md` plays the part that circuit notes play for a model. Write it before the DSP, and keep it up to date as the design changes. Cover:

1. **The idea.** What it should sound like, in words and in measurable terms, and what a player gets from it that existing effects don't give them.
2. **Prior art and inspirations.** Effects, papers, circuits or techniques the idea builds on, as a numbered source list with links. Say what is borrowed and what is new. The [clean-room rule](index.md#ground-rules) still applies: describe and measure, never copy a commercial product.
3. **Block diagram.** Which blocks are new, which come from `pedalkit.lib`, and which are taken from another effect in the repository.
4. **Constants.** Each one with its confidence level and its intent. In an original design most values are *chosen*, which is fine, as long as the notes say what each one is for and how you picked it.
5. **Measurable targets.** What the tests will check to show the idea works, beyond the safety tests every effect has: for example "H2 rises above H3 as Drive passes noon", or "the notch tracks the fundamental within a semitone".
6. **Open questions.** Especially those only a listener can answer.

## Confidence levels for design choices

The same four levels apply as in circuit notes:

| Level | In an original design |
|---|---|
| Documented | Taken from a cited paper, standard or datasheet |
| Reported | Taken from a third party's measurement or description |
| Inferred | Derived from other values, for example a corner frequency set by a target |
| Chosen | A free design decision. Say what it is for and how to retune it. |

## Measuring something new

Without a reference device there is nothing to match, so the tests check the design against its own targets. Add those checks next to the standard ones (silence, peak level, frequency response, harmonics, aliasing; see [Tests and measurements](testing.md)), save their plots and CSV, and describe the results in terms of measurements. The models still can't be listened to by the tools, so every effect page lists what a human should tune by ear.

## Proposing an idea

Open a [new effect issue](https://github.com/Joe-Heffer/faust-pedalkit/issues/new/choose). A rough sonic idea is enough to start a discussion; sources are needed only for the parts that come from existing hardware.
