# faust-pedalkit

Clean-room models of classic guitar and bass pedals, written in Faust and built as native Linux LV2 plugins, with offline measurement tests.

A small repository for building guitar and bass effects in [Faust](https://faust.grame.fr/). Each effect is compiled to an LV2 plugin, with an optional standalone JACK build, and has offline tests that render signals and check them numerically.

| Effect | Description | Notes |
|---|---|---|
| **BassDrive** (`src/bassdrive.dsp`) | Bass overdrive with clean/driven blend and two-band EQ, modelled on a classic compact bass overdrive pedal | [circuit notes](docs/bassdrive/circuit-notes.md) |

## Layout

```text
src/<name>.dsp              one file per effect
src/lib/pedalkit.lib        shared blocks: 4x oversampler, clippers, output safety limiter
docs/<name>/circuit-notes.md  research, sources and modelling decisions
tests/lib/                  render harness (Faust architecture) and Python helpers
tests/<name>/test_*.py      offline tests for one effect
tools/fix-ttl.py            adds LV2 metadata that faust2lv2 cannot write (licence URI, version, class)
tests/run.sh <name>         runs one effect's tests
build/                      generated (bundles, renderers)
tests/out/<name>/           generated plots and WAV renders
```

## Dependencies

| Purpose | Arch | Debian / Ubuntu |
|---|---|---|
| Faust compiler and `faust2lv2` | `faust` | `faust` |
| Boost headers (needed by Faust's LV2 template) | `boost` | `libboost-dev` |
| C++ compiler | `gcc` (or `clang`) | `g++` |
| LV2 headers | `lv2` | `lv2-dev` |
| Standalone JACK build (`faust2jaqt`) | `qt5-base`, `jack2` or `pipewire-jack` | `qtbase5-dev`, `libjack-jackd2-dev` |
| Validation | `lv2lint` | `lv2lint` |
| Quick host for testing | `jalv` | `jalv` |
| Tests | `python-numpy`, `python-matplotlib` | `python3-numpy`, `python3-matplotlib` |
| Optional audio tools | `sox` | `sox` |

Development used Faust 2.88. Older distribution packages may be missing library functions used here, such as `fi.dcblockerat` or `fi.peak_eq_cq`. If the build fails with an "undefined symbol" error from Faust, install a newer Faust (see <https://github.com/grame-cncm/faust/releases>).

### Arch

```sh
sudo pacman -S --needed faust boost gcc lv2 lv2lint jalv sox python-numpy python-matplotlib qt5-base
```

Faust is linked against the system LLVM. If `faust` fails with `libLLVM.so.NN: cannot open shared object file`, the system is partially upgraded. Run `sudo pacman -Syu` to fix it.

### Debian / Ubuntu

```sh
sudo apt install faust libboost-dev g++ lv2-dev lv2lint jalv sox \
                 python3-numpy python3-matplotlib qtbase5-dev libjack-jackd2-dev
```

## Build, test and install

```sh
git clone https://github.com/Joe-Heffer/faust-pedalkit.git
cd faust-pedalkit
```

`faust2lv2` prints "bad port property 'unit:…'" and "'tooltip:…'" messages during the build. These come from a quirk in Faust's LV2 template and are harmless: the units and tooltips are written to the plugin description correctly.

```sh
make lv2                  # build/bassdrive.lv2
make lint                 # lv2lint on every bundle (passes; only an author e-mail warning)
make test                 # renders, checks, and writes plots to tests/out/
make standalone           # build/bassdrive/bassdrive (JACK, Qt GUI)
make install              # copies bundles to ~/.lv2
make uninstall
```

Add `FX=bassdrive` to any target to build one effect only.

Plugin URIs have the form `urn:pedalkit/<name>`, so BassDrive is `urn:pedalkit/bassdrive`.

Quick check from a terminal once it is installed:

```sh
jalv urn:pedalkit/bassdrive          # console host; jalv.gtk3 or jalv.qt5 for a GUI if packaged
```

### Linting and CI

[pre-commit](https://pre-commit.com/) runs the linters and formatters before each commit:

```sh
pipx install pre-commit   # or: pacman -S python-pre-commit
pre-commit install        # once per clone
pre-commit run --all-files
```

| Hook | Checks |
|---|---|
| `ruff-check`, `ruff-format` | Python lint and formatting (config in `pyproject.toml`) |
| `shellcheck` | shell scripts |
| `markdownlint-cli2` | Markdown (config in `.markdownlint-cli2.yaml`) |
| `codespell (typos)` | common misspellings everywhere |
| `codespell (British English)` | American spellings in `.md`, `.dsp` and `.lib` files (word list in `tools/en-gb.codespell`) |
| `faust-compile` | every `src/*.dsp` compiles (needs `faust`) |
| `no-generated-files` | nothing from `build/` or `tests/out/` is committed |
| whitespace, YAML/TOML, shebangs, large files | general hygiene |

GitHub Actions (`.github/workflows/ci.yml`) runs the same hooks, then builds every effect in an Arch Linux container and runs `make lv2 lint test`. The plots and WAV renders from `tests/out/` are uploaded as the `test-output` artifact of each run.

## Loading in a host

All three hosts below find plugins in `~/.lv2` once `make install` has run.

**Ardour.** Ardour scans `~/.lv2` at start-up. If it was already open, use *Window → Plugin Manager → Re-scan*. On a bass track's mixer strip, right-click the processor box, choose *New Plugin → Plugin Selector…*, search for "BassDrive" and add it.

**REAPER (Linux).**

1. Go to *Options → Preferences → Plug-ins → LV2*. Check that `~/.lv2` is in the path list, then click *Re-scan*.
2. Open the track's FX window, choose *Add*, and find "BassDrive" under *LV2*.
3. BassDrive is mono. On a stereo track, REAPER feeds it channel 1, so record bass on a mono track or set the plugin's pin connector.

**Carla.**

1. Open *Settings → Configure Carla → Paths → LV2* and check that `~/.lv2` is listed.
2. Click *Add Plugin*, then *Refresh* with LV2 ticked.
3. Pick "BassDrive". In the patchbay, connect your audio input to it and it to the system outputs.

## BassDrive controls

| Control | Range | Default | What it does |
|---|---|---|---|
| Level | −40 to +12 dB | 0 dB | Output level |
| Balance | 0 to 100 % | 50 % | 0 = clean only, 100 = driven only. The clean path is full-range, so the low end holds up as Gain rises. |
| Gain | 0 to 100 % | 50 % | Drive amount (audio taper) |
| Bass | −12 to +12 dB | 0 dB | Peaking band at 110 Hz |
| Treble | −15 to +15 dB | 0 dB | High shelf from 2.5 kHz |

Every control is smoothed, so automating or turning them does not zipper. The plugin also has a read-only *Latency* output (32 samples) for the host's delay compensation.

**Signal path:** input DC blocker → split into clean and driven paths. The driven path runs pre-emphasis gain (stage 1), then the 4x-oversampled asymmetric clipper, then a DC blocker and a 5 kHz low-pass. The two paths meet at the Balance blend → Bass → fixed −6 dB mid scoop at 350 Hz → Treble → Level → safety limiter (at most −0.1 dBFS). The design reasoning is in [the circuit notes](docs/bassdrive/circuit-notes.md).

**Using it like the original:** the original's High control is already about +10 dB at noon. For that voicing, start from Treble +10 dB. Here 0 dB on Bass and Treble is flat, apart from the fixed mid scoop.

## Measured behaviour

From `make test` at 48 kHz. The plots are in `tests/out/bassdrive/`.

- **Silence in gives silence out.** The output stays below −120 dBFS at all 48 combinations of extreme settings.
- **Peak level.** With every control at maximum and 0 dBFS square waves, noise, sweeps or impulses in, the worst sample is −0.10 dBFS.
- **The low end holds up.** At Balance 50 %, the low E fundamental (41 Hz) varies by only 1.4 dB across the whole Gain range. The clean path alone is flat within ±1.5 dB from 30 to 100 Hz.
- **Harmonics** (single sines, driven path only):

  | Gain | 41 Hz THD | 110 Hz THD | Character |
  |---|---|---|---|
  | 0 % | 2.2 % | 1.4 % | light, odd-order |
  | 50 % | 5.9 % | 12.5 % | H2 overtakes H3 at 110 Hz (warm, even-leaning) |
  | 100 % | 30.5 % | 27.5 % | heavy, odd-order dominant, harmonics strong up to the 10th |

- **Frequency response of the driven path.** It rises from about 300 Hz to a broad peak at 1–3 kHz, and the peak grows with Gain (about +3 dB at Gain 0, +25 dB at noon, +36 dB at maximum for small signals). It then falls steeply above about 5 kHz. This is the treble-forward, "grind on top of the clean low end" voicing the original is known for.
- **Fixed mid scoop.** About 5–6 dB at 350 Hz, matching the published measurement of the original.
- **Aliasing.** Against a 1x build of the same DSP, 4x oversampling lowers the worst alias by 22 dB for a 3.7 kHz tone and by 30 dB for a 1.1 kHz tone at full Gain. The worst alias at 1.1 kHz is −65 dBc.

## What to tune by ear

These are measured approximations, not listening-tested. Each item below names the control or `src/bassdrive.dsp` constant to change.

1. **The blend notch.** With Balance near 50 % and Gain high, the two paths cancel at about 6–8 kHz. Listen for a hollow or phasey top end. `postLP` moves it, and `drvTrim` changes its depth.
2. **How lopsided the drive is.** `ledNeg` (−0.8 V) and `negKnee` (6) set how quickly the sound turns warm and even-order as Gain rises. Raise `ledNeg` towards 1.7 for a more symmetric, harder sound.
3. **Overall drive range.** `stage2G` (3.0) and the 303 in `hfGain` set how much distortion there is at each Gain position.
4. **The mid scoop.** `scoopDB` (−6 dB). Try −3 dB for a fuller mix sound, or 0 to remove it.
5. **Fizz.** `postLP` (5 kHz) and Treble. If high Gain sounds buzzy, lower `postLP` towards 3.5 kHz.
6. **Clean/driven loudness.** `drvTrim` (0.28). Set it so that sweeping Balance at your usual Gain doesn't change the perceived volume.
7. **Input level.** The model treats 0 dBFS as 1 V at the pedal's input. If your interface records the bass hot or quiet, every Gain setting will feel shifted, so adjust your input gain before changing the constants.

## Known limitations

- **It isn't a full circuit simulation.** The drive stage is modelled as linear filters around a memoryless waveshaper (static nonlinearity). Effects that depend on the circuit's history are not captured: bias shifting under heavy playing, supply sag, and interaction between the clipper and the filters around it. Fast transients therefore compress a little more neatly than real hardware does.
- **Several values are educated guesses.** These are the Gain pot taper and range, the stage-2 gain, the clipping asymmetry and the post-filter. Each one is marked as "chosen" in the circuit notes, and all are named constants near the top of `src/bassdrive.dsp`.
- **The tone stack doesn't interact.** The EQ bands are independent digital filters, whereas a passive or active network would interact.
- **Latency.** The oversampler adds 32 samples (0.67 ms at 48 kHz). It is compensated inside the plugin between the clean and driven paths, and reported to the host through an LV2 latency port, so hosts that support plugin delay compensation will line the track up.
- **Mono only.**
- **Some aliasing remains.** At extreme Gain with very high-pitched material, some aliasing remains despite the 4x oversampling. The safety limiter runs at the base rate and can alias if you drive it hard with Level.

## Licence

MIT; see [LICENSE](LICENSE). BassDrive is an independent model built from public information. It is not affiliated with, or endorsed by, any pedal manufacturer, and no proprietary code was used.
