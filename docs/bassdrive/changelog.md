# BassDrive changelog

Notable changes to BassDrive. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the version, `declare version` in `src/bassdrive.dsp`, follows [Semantic Versioning](https://semver.org/). Each release is tagged `bassdrive-vX.Y.Z` (see [Releasing](../development/releasing.md)).

## [Unreleased]

### Fixed

- CPU use no longer climbs after the input falls silent. Filter state that decays below the smallest normal float is now flushed to zero (Faust's `-ftz 1`) in every format. Before, the LV2 plug-in, in a host that leaves the FPU's flush-to-zero off, spent 22 times as much CPU on a decaying tail as on live signal. The VST3 and CLAP plug-ins already flushed subnormals and are unchanged. The browser demo is built with the same flag.

## [0.1.0]

First release: Linux x86_64 plugins in LV2, VST3 and CLAP formats, with an `install.sh` that installs them into `~/.lv2`, `~/.vst3` and `~/.clap`.

### Added

- Bass overdrive with a clean/driven blend, two-band EQ and a fixed mid scoop, with the clipper 4x oversampled.

[Unreleased]: https://github.com/Joe-Heffer/faust-pedalkit/compare/bassdrive-v0.1.0...HEAD
[0.1.0]: https://github.com/Joe-Heffer/faust-pedalkit/releases/tag/bassdrive-v0.1.0
