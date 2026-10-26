# Where this project sits

Faust Pedal Kit is one of several open-source projects in guitar and bass effect design. This page maps the neighbours, says what each is good for, and sets out what this project does differently. It is also a reading list: most of the projects below are worth studying before you start a new effect.

The survey comes from a web search in October 2026. Most of it rests on package listings, mailing-list posts and repository descriptions, and the pages were not all opened in full. Treat licences, activity and feature claims as leads to confirm at the source before relying on them. Corrections are welcome through the [issue tracker](https://github.com/Joe-Heffer/faust-pedalkit/issues).

## The neighbours

### Faust-based guitar effects

* **Guitarix** is a Linux guitar amp and effects host for JACK, with its amp and effect modules written in Faust ([Arch package](https://archlinux.org/packages/extra/x86_64/guitarix/), [Faust community page](https://faust.grame.fr/community/powered-by-faust/)). It is the closest relative of this project and the largest body of open Faust guitar DSP. Its authors have generated LV2 bundles from Faust sources with their own scripts, which a [MOD Audio forum thread](https://forum.mod.audio/t/from-faust-to-mod-plugin/332) describes as limited to effects with equal numbers of input and output ports.
* **gxplugins.lv2** packages a set of analogue pedal simulations from Guitarix as standalone LV2 plugins ([Linux Audio wiki](https://wiki.linuxaudio.org/_export/xhtml/apps/all/gxplugins.lv2)).
* **FatFrog and LittleFly** are a high-gain amp and an overdrive by Hermann Meyer, reported as BSD-0 licensed with Faust source included ([announcement](https://lists.linuxaudio.org/archives/linux-audio-dev/2020-June/037810.html)).
* **Kapitonov's plugin pack** is a set of LADSPA and LV2 guitar plugins ([Nixpkgs commit](https://code.ornl.gov/nix/nixpkgs/-/commit/037324b6f878b732d102a6cb8ef327c71087eb42)).
* Faust's own library has distortion building blocks such as `cubicnl` ([Julius O. Smith's description](https://ccrma.stanford.edu/~jos/pasp/Software_Cubic_Nonlinear_Distortion.html)).

### Circuit modelling

* **KlonCentaur** by Jatin Chowdhury is a C++ model of a well-known overdrive pedal, built from nodal analysis, wave digital filters and a recurrent neural network, and released under BSD-3-Clause ([repository](https://github.com/jatinchowdhury18/KlonCentaur)). The search results suggest it has had no commits since 2021.
* **moForte** sells guitar products it says are implemented entirely in Faust, including circuit-level distortion and amp models ([product literature](https://www.moforte.com/wp-content/uploads/2019/01/A3E.pdf)). It is commercial and closed, so it is background only. Under this project's [clean-room rule](development/index.md#ground-rules) it is never a reference to match against.
* A [2020 AES paper](https://hal-lara.archives-ouvertes.fr/GRAME/hal-03087763v1) covers Faust and the recreation of tube amplifiers and pedalboards in web browsers.

### Open hardware and programmable pedals

* **OWL** is a reprogrammable pedal on an ARM Cortex-M4, programmed in C or C++ ([Synthtopia](https://www.synthtopia.com/content/2013/05/31/owl-programmable-effects-pedal/)).
* **Bela pedal** by Lehel Török pairs a KiCad extension board with Pure Data patches ([Bela blog](https://blog.bela.io/effects-pedal-lehel-torok/)).
* **pedalSHIELD UNO** is an open-hardware Arduino pedal ([Hackster](https://www.hackster.io/electrosmash/arduino-uno-guitar-pedal-b2ba96)).
* **DaisySeedProjects** and **Funbox** hold firmware and KiCad files for pedals built on the Daisy Seed ([repository](https://github.com/bkshepherd/DaisySeedProjects)).
* **Pédale Vite** is a Raspberry Pi multi-effects pedalboard ([listing](https://fr.github.com/EleonoreMizo/pedalevite)).
* The **Spin FV-1 emulator** runs FV-1 programs on a PC before they are flashed ([Hackaday](https://hackaday.com/2026/09/12/spin-fv-1-emulator-simplifies-sound-pedal-development/)).

### General plugin suites

* **LSP** ([lsp-plug.in](https://lsp-plug.in/)) ships dynamics, equalisation, reverb and more in CLAP, LV2, VST2 and VST3.
* **zam-plugins** ([repository](https://github.com/zamaudio/zam-plugins)) is a GPL collection of LADSPA, LV2 and VST plugins.
* **Wolf Shaper** offers a spline-based waveshaper, which is useful for sketching transfer curves before committing them to Faust.
* **ScorchCrafter C120** is an amp-head emulator reported as GPL from version 3.0 ([forum post](https://community.ardour.org/node/4128)).

### Text-to-plugin generators

* **Pluginmaker.ai** is a browser tool that turns a text description into a plugin. You preview the result with a MIDI controller, an on-screen keyboard, your own audio or a built-in sequencer, then export it. Launch coverage from March 2026 describes exports to VST and AU, a beta product, and 300 free credits for new users ([SonicState](https://sonicstate.com/news/2026/03/27/pluginmakerai-/)). A comparison piece reports a paid subscription with a marketplace commission ([blog](https://blog.imseankim.com/?p=9782)). It is closed and commercial. No official documentation was found, so its DSP, its export pipeline and whether it targets VST3 or CLAP are unconfirmed.
* **MATLAB’s `generateAudioPlugin`** builds a VST plugin from a MATLAB audio plugin class ([MathWorks reference](https://www.mathworks.com/help/audio/ref/generateaudioplugin.html)). It is a commercial numerical environment aimed at engineers rather than pedal designers. Its output format was not checked.

## What is different here

None of the projects above combines all of the following. Several do some of them well.

* **New sounds are the aim.** Most neighbours reproduce an existing amp or pedal, or offer a platform to run effects on. Here, [modelling hardware](development/designing-new-sounds.md) is a way to learn how a circuit gets its character and to collect building blocks. The preferred output is an original or circuit-inspired effect that does something a box of components could not.
* **Measurement stands in for listening.** Every effect has offline tests that render signals through the compiled DSP and check silence, peak level, frequency response, harmonics and aliasing, with the plots and the numbers behind them (CSV) published on this site. Sound is judged by [measurement](development/testing.md), and the notes list what a human should tune by ear.
* **Every constant is accounted for.** Each value is marked documented, reported, inferred or chosen, with a source or an intent. This is rare in plugin projects, where constants are often unexplained.
* **Clean-room and licensing rules are enforced by tooling.** Pre-commit hooks check for trademarks in names and sources and for SPDX headers, and the [REUSE](https://reuse.software/) specification makes every file's licence machine-readable. Code is MIT and documentation is CC BY 4.0.
* **One Faust file, three formats.** A single `.dsp` builds LV2, VST3 and CLAP plugins. The VST3 and CLAP wrappers are this repo's own architectures written against the permissively licensed SDKs, so the plugins avoid the JUCE licensing question. All three formats share the same checked presets. The same file also compiles to WebAssembly for the [browser demo](usage/browser.md), and a test compares that output with the native renderer.
* **Schematics are generated and checked.** Where an effect models a circuit, its KiCad schematic is produced by a script that asserts every corner frequency and gain quoted in the notes, so the drawing, the notes and the DSP cannot drift apart unnoticed.
* **Plugins come from reviewed design, not a prompt.** A text-to-plugin generator goes from an idea to a plugin in one step. Here an effect starts as design notes, is written by hand in Faust (coding agents may help with that), and ships only when its constants are accounted for and its tests pass. Generated DSP would need the same review, so it could not skip the notes.
* **The workflow suits coding agents.** [`AGENTS.md`](https://github.com/Joe-Heffer/faust-pedalkit/blob/main/AGENTS.md) and a Claude Code skill describe the whole path from notes to released plugin, with checks that fail loudly.

## Limits and trade-offs

* Slower to a first sound than a text-to-plugin generator. An effect starts with notes and hand-written Faust, and the path from idea to a released plugin is longer.
* Linux only. Guitarix and the Faust ecosystem have a longer history and a far larger library of effects and amp models.
* Plugins have no custom graphical interface. Hosts show generic controls.
* Three effects exist so far, and only one is circuit-inspired. There is no original design yet.
* Models are measured against sources and numerical targets, not against listening tests. Whether they sound right is for a human to decide.
* The neural and wave-digital-filter approaches seen in KlonCentaur are not used here. Effects are hand-structured Faust, which keeps them readable and portable but may fit some nonlinear circuits less closely.

## Gaps and where to look next

* The search found no Faust wah model and no consolidated list of Faust pedal plugins.
* It did not cover wave digital filter or diode-clipper research, which is the likeliest source of new circuit-level blocks for [`pedalkit.lib`](development/pedalkit-lib.md).
* Guitarix's source tree is the first place to check before writing a block that may already exist in Faust. Check its licence before porting anything, since a licence incompatible with MIT would rule out copying code, and the [clean-room rule](development/index.md#ground-rules) applies to every outside source.
