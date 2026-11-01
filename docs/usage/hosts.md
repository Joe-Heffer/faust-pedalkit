# Loading in a host

Install an effect first: [download](../download.md) it and run `./install.sh`, which puts the plugins in `~/.lv2`, `~/.vst3` and `~/.clap`. Every common Linux host scans those folders. The plugins are mono, take their names from the effect (for example “BassDrive”), and report their latency to the host so it can compensate.

!!! note "Built from source?"
    `make install`, `make install-vst3` and `make install-clap` copy the LV2, VST3 and CLAP builds into the same folders (see [Build from source](../install.md)).

## Ardour

Ardour scans `~/.lv2` at start-up. If it was already open, use *Window → Plugin Manager → Re-scan*.

On the track's mixer strip, right-click the processor box, choose *New Plugin → Plugin Selector…*, search for the effect's name and add it.

## REAPER (Linux)

The [REAPER guide](reaper.md) covers this in more detail, including input level, latency and presets.

1. Go to *Options → Preferences → Plug-ins* and choose *CLAP*, *VST* or *LV2*. Check that `~/.clap`, `~/.vst3` or `~/.lv2` is in the path list, then click *Re-scan*.
2. Open the track's FX window, choose *Add*, and find the effect under *CLAP*, *VST3* or *LV2*.
3. The effects are mono. On a stereo track, REAPER feeds a mono plugin channel 1, so record onto a mono track or set the plugin's pin connector.

## Carla

1. Open *Settings → Configure Carla → Paths → LV2* and check that `~/.lv2` is listed.
2. Click *Add Plugin*, then *Refresh* with LV2 ticked.
3. Pick the effect. In the patchbay, connect your audio input to it and it to the system outputs.

## jalv

`jalv` is the quickest way to hear a plugin without a DAW:

```sh
jalv urn:pedalkit/bassdrive
```

Connect its ports with your patchbay of choice (`qpwgraph`, `helvum` or Carla on PipeWire).

## Latency

Effects that oversample add a fixed delay, which they report to the host (through an LV2 latency port, the VST3 latency call or the CLAP latency extension). BassDrive adds 32 samples (0.67 ms at 48 kHz) and BassPreamp, with two oversampled stages, adds 64 samples (1.3 ms). Hosts with plugin delay compensation, including Ardour and REAPER, use the reported value to line the track up with the others.

## Input level

The models treat 0 dBFS as 1 V at the pedal's input. A DI'd bass or guitar peaking around −12 dBFS is a sensible starting point. If your interface records hot or quiet, every drive setting will feel shifted, so set the input gain before reaching for the plugin's controls.
