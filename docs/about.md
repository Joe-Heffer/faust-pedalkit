# About

Faust Pedal Kit is a workshop for designing new guitar and bass effects in Faust, with clean-room models of classic pedals as a source of building blocks. It is maintained by Joe Heffer on [GitHub](https://github.com/Joe-Heffer/faust-pedalkit). Bug reports, questions and contributions go to the [issue tracker](https://github.com/Joe-Heffer/faust-pedalkit/issues).

For how this project relates to similar open-source work, see [Where this project sits](ecosystem.md).

## How the effects are made

New to DSP or Faust? [How it works](development/how-it-works.md) explains what an effect is in code, how Faust describes it, and how one `.dsp` file becomes LV2, VST3 and CLAP plugins plus measurements.

**Ideas first, models as a means.** An effect is *original* (a sonic idea with no single reference device), *circuit-inspired* (a real circuit taken somewhere it couldn't go), or *modelled* (a measured, sourced model of one device). Original effects are documented in design notes, models in circuit notes. Clean-room models of well-known circuits show how they get their character and supply tested building blocks (clippers, analogue filter sections, voicings) that original designs can reuse, bend and recombine. See [Designing new sounds](development/designing-new-sounds.md) for where the project is heading.

**Clean-room.** Anything taken from existing hardware is built from public schematics, circuit analyses, measurements, reviews and manuals. No proprietary plugin, binary or firmware is decompiled, disassembled or used as a reference.

**Every value has a confidence level.** The design and circuit notes mark each value and design decision as one of:

| Level | Meaning |
|---|---|
| Documented | Stated by the manufacturer |
| Reported | Stated by one or more third parties, such as a forum post, review or measurement |
| Inferred | Reasoned from the reported facts |
| Chosen | A free design choice, with its intent stated |

The chosen values are named constants at the top of each `.dsp` file, so you can retune them.

**Measured, then tuned by ear.** The effects are judged by measurement: harmonics, frequency response, aliasing and levels. Each effect page shows the current measurements and lists the constants a human should tune by ear.

**Neutral names.** Plugins carry no manufacturer branding. Product names appear in the docs only to identify reference or inspiring hardware.

## Licence

- **Code** (the Faust DSP, build tools and tests) is [MIT](https://github.com/Joe-Heffer/faust-pedalkit/blob/main/LICENSE).
- **Documentation** (everything under `docs/`, including this site and the design and circuit research) is [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Every file's licence is machine-readable, following the [REUSE](https://reuse.software/) specification: each source file has an SPDX header, and `REUSE.toml` covers the rest.

## Trademarks and affiliation

The effects are independent designs and models built from public information. They are not affiliated with, or endorsed by, any pedal manufacturer, and no proprietary code was used. Manufacturer and product names appear in the notes only to identify reference or inspiring hardware, and remain the property of their owners.
