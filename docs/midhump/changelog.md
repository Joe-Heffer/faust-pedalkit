# MidHump changelog

Notable changes to MidHump. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the version, `declare version` in `src/midhump.dsp`, follows [Semantic Versioning](https://semver.org/). Each release is tagged `midhump-vX.Y.Z` (see [Releasing](../development/releasing.md)).

## [Unreleased]

### Fixed

- CPU use no longer climbs after the input falls silent. Filter state that decays below the smallest normal float is now flushed to zero (Faust's `-ftz 1`) in every format. Before, the LV2 plug-in, in a host that leaves the FPU's flush-to-zero off, spent 33 times as much CPU on a decaying tail as on live signal. The VST3 and CLAP plug-ins already flushed subnormals and are unchanged. The browser demo is built with the same flag.

## [0.1.0]

First release.

### Added

- Mid-hump overdrive with Drive, Tone and Level, and an optional full-range clean Blend. The diode clipper is 4x oversampled.
- Four factory presets (Edge of Breakup, Mid Hump, Lead, Bass Grind) in the LV2, VST3 and CLAP plugins.

[Unreleased]: https://github.com/Joe-Heffer/faust-pedalkit/compare/midhump-v0.1.0...HEAD
[0.1.0]: https://github.com/Joe-Heffer/faust-pedalkit/releases/tag/midhump-v0.1.0
