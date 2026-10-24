# Install and build

The effects build on Linux into LV2 plugin bundles, plus an optional standalone JACK application per effect.

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

Development used Faust 2.88. Older distribution packages may lack library functions used here, such as `fi.dcblockerat` or `fi.peak_eq_cq`. If Faust stops with an "undefined symbol" error, install a newer release from [the Faust releases page](https://github.com/grame-cncm/faust/releases).

### Arch

```sh
sudo pacman -S --needed faust boost gcc lv2 lv2lint jalv sox python-numpy python-matplotlib qt5-base
```

Faust links against the system LLVM. If `faust` fails with `libLLVM.so.NN: cannot open shared object file`, the system is partially upgraded, and `sudo pacman -Syu` fixes it.

### Debian / Ubuntu

```sh
sudo apt install faust libboost-dev g++ lv2-dev lv2lint jalv sox \
                 python3-numpy python3-matplotlib qtbase5-dev libjack-jackd2-dev
```

## Get the source

```sh
git clone https://github.com/Joe-Heffer/faust-pedalkit.git
cd faust-pedalkit
```

## Build, test and install

```sh
make lv2                  # build/<name>.lv2 for every effect
make lint                 # lv2lint on every bundle
make test                 # offline tests; SVG plots and CSV data in tests/out/
make describe             # each effect's controls (JSON) and block diagram (SVG)
make standalone           # build/<name>/<name>, a JACK application with a Qt GUI
make install              # copy the bundles into ~/.lv2
make uninstall            # remove them again
make clean                # remove build/ and tests/out/
```

Every target builds all effects by default. Add `FX=<name>` to build one, for example `make lv2 FX=bassdrive`.

!!! note "Harmless build messages"
    `faust2lv2` prints "bad port property 'unit:…'" and "'tooltip:…'" messages. They come from a quirk in Faust's LV2 template. The units and tooltips still reach the plugin description, because `tools/fix-ttl.py` rewrites the metadata after the build.

## Plugin URIs

Each plugin's URI is `urn:pedalkit/<name>`, so BassDrive is `urn:pedalkit/bassdrive`. To try one from a terminal once it is installed:

```sh
jalv urn:pedalkit/bassdrive     # console host; jalv.gtk3 or jalv.qt5 give a GUI where packaged
```

On a PipeWire system with `pipewire-jack`, JACK hosts and the standalone builds run without a separate JACK daemon.

## Repository layout

```text
src/<name>.dsp                  one file per effect
src/lib/pedalkit.lib            shared blocks: 4x oversampler, clippers, output safety limiter
docs/                           this site; docs/<name>/circuit-notes.md holds each effect's research
tests/lib/                      render harness (a Faust architecture) and Python helpers
tests/<name>/test_*.py          offline tests for one effect
tests/run.sh <name>             runs one effect's tests
tools/fix-ttl.py                adds LV2 metadata faust2lv2 cannot write (licence URI, version, class)
tools/mkdocs_hooks.py           publishes test plots and data on this site
build/                          generated: bundles, renderers, this site
tests/out/<name>/               generated: plots (SVG), data (CSV) and renders (WAV)
```
