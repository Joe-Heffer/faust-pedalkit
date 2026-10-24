# Loading in a host

After `make install`, the bundles are in `~/.lv2`, which every common Linux LV2 host scans. The plugins are mono, take their names from the effect (for example "BassDrive"), and report their latency to the host so it can compensate.

For VST3, run `make install-vst3` instead. It copies the bundles to `~/.vst3`, the standard per-user VST3 folder on Linux, which REAPER, Bitwig, Ardour and Carla scan; the effects then appear in their VST3 lists under the same names.

For CLAP, run `make install-clap`. It copies the plugins to `~/.clap`, the per-user CLAP folder on Linux, which REAPER, Bitwig and Carla scan. In REAPER the effects are listed under *CLAP* in the FX browser; if they don't appear, use *Options → Preferences → Plug-ins → CLAP → Re-scan*.

## Ardour

Ardour scans `~/.lv2` at start-up. If it was already open, use *Window → Plugin Manager → Re-scan*.

On the track's mixer strip, right-click the processor box, choose *New Plugin → Plugin Selector…*, search for the effect's name and add it.

## REAPER (Linux)

1. Go to *Options → Preferences → Plug-ins → LV2*. Check that `~/.lv2` is in the path list, then click *Re-scan*.
2. Open the track's FX window, choose *Add*, and find the effect under *LV2*.
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

Effects that oversample add a fixed delay, which they report to the host (through an LV2 latency port, the VST3 latency call or the CLAP latency extension). BassDrive adds 32 samples, which is 0.67 ms at 48 kHz. Hosts with plugin delay compensation, including Ardour and REAPER, use the reported value to line the track up with the others.

## Input level

The models treat 0 dBFS as 1 V at the pedal's input. A DI'd bass or guitar peaking around −12 dBFS is a sensible starting point. If your interface records hot or quiet, every drive setting will feel shifted, so set the input gain before reaching for the plugin's controls.
