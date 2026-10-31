# Download

Every effect is free, under the MIT licence. Pick an effect, download it, run the installer and rescan plugins in your DAW.

<!-- downloads:all -->

Not sure which effect you want? [Play them in your browser](demo/index.html) first, or read about each one on the [effects page](effects/index.md).

## Which file do I need?

Each download holds one effect in all three plugin formats, plus the installer. The formats sound the same, so you only need the one your DAW loads, and `./install.sh` installs all three unless you name some (see [Install](#install)).

| Your DAW | Format it loads best |
|---|---|
| REAPER, Bitwig Studio | **CLAP**, the newest format and fully open |
| Ardour, Carla, Qtractor and other LV2 hosts | **LV2** |
| Any other host that loads VST3 plugins | **VST3** |

## Requirements

* 64-bit Linux (x86_64) with glibc 2.35 or newer: Ubuntu 22.04, Debian 12 or later, Linux Mint 21 or later, or any current rolling distribution such as Arch or Fedora. Run `ldd --version` to see your glibc version.
* A plugin host: a DAW such as REAPER, Bitwig Studio or Ardour, or Carla.
* A mono input, such as a bass or guitar plugged into an audio interface. A DI'd signal peaking around −12 dBFS is a good starting level.

There are no macOS or Windows builds yet. On those systems you can [play the effects in your browser](demo/index.html).

## Install

Each download is a `.tar.gz` file holding the plugins, the effect's changelog and an installer, `install.sh`. In a terminal, in the folder you downloaded it to:

```sh
tar -xzf bassdrive-*-linux-x86_64.tar.gz   # or whichever effect you downloaded
cd bassdrive-*-linux-x86_64/
./install.sh
```

`install.sh` copies the plugins into `~/.lv2`, `~/.vst3` and `~/.clap`, the folders in your home directory that Linux DAWs scan. It needs no root and touches only the plugins in the download, replacing any older copies of them. Then rescan plugins in your DAW (see [below](#the-effect-doesnt-show-up)).

| Command | What it does |
|---|---|
| `./install.sh` | install every format in the download |
| `./install.sh --lv2 --clap` | install only the formats named (`--lv2`, `--vst3`, `--clap`) |
| `./install.sh --uninstall` | remove the plugins again; combine with format flags to remove only some |
| `LV2DIR=… VST3DIR=… CLAPDIR=… ./install.sh` | install into other folders |

To check the download first, save the release's `SHA256SUMS` file next to it and run `sha256sum -c --ignore-missing SHA256SUMS`.

## The effect doesn't show up

Most DAWs only look for new plugins when asked:

* **REAPER:** *Options → Preferences → Plug-ins → CLAP* (or *VST* or *LV2*), then *Re-scan*. The effect is listed under its name, such as “BassDrive”, in the FX browser.
* **Ardour:** restart it, or use *Window → Plugin Manager → Re-scan*.
* **Carla:** *Add Plugin*, then *Refresh*.

The effects are mono, so put them on a mono track, or check which channel the host feeds them (REAPER uses channel 1 of a stereo track). [Loading in a host](usage/hosts.md) and the [REAPER guide](usage/reaper.md) go into more detail, including latency and presets.

If the plugin still doesn't load, your system may be older than the requirements above. [Building from source](install.md) works on older systems, or [open an issue](https://github.com/Joe-Heffer/faust-pedalkit/issues) with your distribution and DAW.

## Updates and older versions

Each effect is released on its own, with its own version number and changelog (linked from each effect's page). To update, download the new version and run `./install.sh` again; it replaces the old copy. Older versions are on the [releases page](https://github.com/Joe-Heffer/faust-pedalkit/releases), tagged `<name>-v<version>`, for example `bassdrive-v0.1.0`.
