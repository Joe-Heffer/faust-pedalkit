# Build from source

!!! tip "Just want to play?"
    You don't need to build anything to use the effects. [Download](download.md) a release and run its installer.

Build from source to change an effect, add one of your own, run the tests, or use the plugins on a system older than the releases support. The effects build on Linux into LV2, VST3 and CLAP plugins, plus an optional standalone JACK application per effect.

## Dependencies

| Purpose | Arch | Debian / Ubuntu |
|---|---|---|
| Faust compiler and `faust2lv2` | `faust` | `faust` |
| Boost headers (needed by Faust's LV2 template) | `boost` | `libboost-dev` |
| C++ compiler | `gcc` (or `clang`) | `g++` |
| LV2 headers | `lv2` | `lv2-dev` |
| Standalone JACK build (`faust2jaqt`) | `qt5-base`, `jack2` or `pipewire-jack` | `qtbase5-dev`, `libjack-jackd2-dev` |
| VST3 build (fetches the VST3 SDK into `build/`) | `cmake`, `git` | `cmake`, `git` |
| CLAP build (fetches the CLAP headers into `build/`) | `git` | `git` |
| Validation | `lv2lint`; [pluginval](https://github.com/Tracktion/pluginval/releases) for VST3; [clap-validator](https://github.com/free-audio/clap-validator/releases) for CLAP | `lv2lint`; pluginval; clap-validator |
| Quick host for testing | `jalv` | `jalv` |
| Tests | `python-numpy`, `python-matplotlib` | `python3-numpy`, `python3-matplotlib` |
| Optional audio tools | `sox` | `sox` |

Development used Faust 2.88. Older distribution packages may lack library functions used here, such as `fi.dcblockerat` or `fi.peak_eq_cq`. If Faust stops with an "undefined symbol" error, install a newer release from [the Faust releases page](https://github.com/grame-cncm/faust/releases).

### Arch

```sh
sudo pacman -S --needed faust boost gcc lv2 lv2lint jalv sox python-numpy python-matplotlib qt5-base \
                        cmake git
```

Faust links against the system LLVM. If `faust` fails with `libLLVM.so.NN: cannot open shared object file`, the system is partially upgraded, and `sudo pacman -Syu` fixes it.

### Debian / Ubuntu

```sh
sudo apt install faust libboost-dev g++ lv2-dev lv2lint jalv sox cmake git \
                 python3-numpy python3-matplotlib qtbase5-dev libjack-jackd2-dev
```

## In a container (any OS)

If your distribution's Faust is too old, or you are on macOS or Windows (WSL), build and test inside the toolchain image instead. The `Dockerfile` pins Faust and the other tools to a dated Arch Linux snapshot, and CI uses the same image. Only Docker or Podman is needed on the host.

```sh
make container                            # builds the image, then runs make lv2 lint test inside it
make container RUN="describe" FX=bassdrive
make container RUN="vst3 pluginval"
make container CONTAINER=podman           # Podman instead of Docker
```

The repository is mounted into the container, so the results land in `build/` and `tests/out/` as usual, owned by you. `CONTAINER_FLAGS` passes extra options to `docker run`, for example `CONTAINER_FLAGS="--dns 1.1.1.1"` if containers on your machine cannot resolve host names. Run `make install` and the listening hosts (`jalv`, a DAW) on the host, not in the container.

The bundles are built against Arch's current glibc, so they may not load on older distributions, such as an Ubuntu LTS release. They are Linux binaries, so they don't run in macOS or Windows hosts either. Use the container to build and test, and build natively for the machine you play on.

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
make vst3                 # build/<name>.vst3 (fetches the VST3 SDK on first use)
make pluginval            # pluginval at strictness 10 on every VST3 bundle
make install-vst3         # copy the VST3 bundles into ~/.vst3
make clap                 # build/<name>.clap (fetches the CLAP headers on first use)
make clap-validate        # clap-validator on every CLAP plugin
make install-clap         # copy the CLAP plugins into ~/.clap
make uninstall            # remove all three again
make clean                # remove build/ and tests/out/
```

Every target builds all effects by default. Add `FX=<name>` to build one, for example `make lv2 FX=bassdrive`.

## VST3

The VST3 build uses Steinberg's [VST3 SDK](https://github.com/steinbergmedia/vst3sdk), which has been MIT-licensed since version 3.8. `make vst3` clones a pinned release into `build/vst3sdk` (only the submodules it needs), or uses an existing checkout given as `VST3_SDK=/path/to/vst3sdk`. The SDK's validator runs on each bundle as part of the build. For `make pluginval`, download pluginval and put it on `PATH`, or pass `PLUGINVAL=/path/to/pluginval`. The VST3 plugins have no custom GUI, so hosts show their generic parameter editor.

## CLAP

The CLAP build needs only the MIT-licensed [CLAP headers](https://github.com/free-audio/clap). `make clap` clones a pinned release into `build/clap`, or uses an existing checkout given as `CLAP_SDK=/path/to/clap`. For `make clap-validate`, download [clap-validator](https://github.com/free-audio/clap-validator/releases) and put it on `PATH`, or pass `CLAP_VALIDATOR=/path/to/clap-validator`. The CLAP plugins have no custom GUI either.

!!! note "Harmless build messages"
    `faust2lv2` prints "bad port property 'unit:…'" and "'tooltip:…'" messages. They come from a quirk in Faust's LV2 template. The units and tooltips still reach the plugin description, because `tools/fix-ttl.py` rewrites the metadata after the build.

## Plugin URIs

Each plugin's URI is `urn:pedalkit/<name>`, so BassDrive is `urn:pedalkit/bassdrive`. The CLAP plugin ID is `pedalkit.<name>`, here `pedalkit.bassdrive`. To try one from a terminal once it is installed:

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
tools/vst3/                     VST3 architecture (Faust) and CMake project for the VST3 SDK
tools/vst3-meta.py              writes each VST3 plugin's name, version, category and class ID
tools/clap/faust-clap.cpp       CLAP architecture (Faust), written against the CLAP headers
tools/clap-meta.py              writes each CLAP plugin's ID, name, version and features
build/                          generated: bundles, renderers, this site
tests/out/<name>/               generated: plots (SVG), data (CSV) and renders (WAV)
```
