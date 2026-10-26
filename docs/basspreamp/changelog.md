# BassPreamp changelog

Notable changes to BassPreamp. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the version, `declare version` in `src/basspreamp.dsp`, follows [Semantic Versioning](https://semver.org/). Each release is tagged `basspreamp-vX.Y.Z` (see [Releasing](../development/releasing.md)).

## [Unreleased]

### Fixed

- CPU use no longer climbs after the input falls silent. Filter state that decays below the smallest normal float is now flushed to zero (Faust's `-ftz 1`) in every format. Before, the LV2 plug-in, in a host that leaves the FPU's flush-to-zero off, spent 4.7 times as much CPU on a decaying tail as on live signal. The VST3 and CLAP plug-ins already flushed subnormals and are unchanged. The browser demo is built with the same flag.

### Added

- Factory presets in the VST3 plugin (as its program list) and the CLAP plugin (through preset discovery), the same seven as in LV2.

## [0.1.0]

First release: Linux x86_64 plugins in LV2, VST3 and CLAP formats, with an `install.sh` that installs them into `~/.lv2`, `~/.vst3` and `~/.clap`.

### Added

- Tube-voiced bass preamp/DI with blend, presence, speaker voicing and a three-band EQ.
- Cab Bypass switch, which removes the speaker voicing for use with a real cabinet or an impulse response.
- Factory presets (LV2).

[Unreleased]: https://github.com/Joe-Heffer/faust-pedalkit/compare/basspreamp-v0.1.0...HEAD
[0.1.0]: https://github.com/Joe-Heffer/faust-pedalkit/releases/tag/basspreamp-v0.1.0
