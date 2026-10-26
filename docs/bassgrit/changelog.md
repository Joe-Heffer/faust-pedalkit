# BassGrit changelog

Notable changes to BassGrit. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the version, `declare version` in `src/bassgrit.dsp`, follows [Semantic Versioning](https://semver.org/). Each release is tagged `bassgrit-vX.Y.Z` (see [Releasing](../development/releasing.md)).

## [Unreleased]

## [0.1.0]

First release.

### Added

- Six factory presets (Edge of Grit, Mid Grit, Full Grit, Clean Sub, Dark Growl, Five-String), loudness-matched on a bass line, in LV2, VST3 and CLAP.
- KiCad schematic of the modelled circuit, with the circuit notes' values now reported from a public parts list and schematic.
- Hard-clipping distortion for bass, with Distortion, Filter, Level, Low Blend and Crossover. A 4th-order Linkwitz-Riley split keeps the low band out of the 4x oversampled diode clipper.

[Unreleased]: https://github.com/Joe-Heffer/faust-pedalkit/compare/bassgrit-v0.1.0...HEAD
[0.1.0]: https://github.com/Joe-Heffer/faust-pedalkit/releases/tag/bassgrit-v0.1.0
