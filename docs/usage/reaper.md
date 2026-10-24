# Using the effects in REAPER (Linux)

This guide takes you from a built plugin to a track in REAPER. It applies to every effect in the kit; the examples use BassPreamp. It assumes a mono input, such as a DI or an instrument input on your interface. For other hosts, see [Loading in a host](hosts.md).

## 1. Build and install

Pick one plugin format. REAPER loads all three, so there is no need to install more than one.

```sh
make lv2 lint test FX=basspreamp   # build, lint and run the offline tests
make install FX=basspreamp         # LV2: copies build/basspreamp.lv2 to ~/.lv2

make vst3 install-vst3 FX=basspreamp   # or VST3, into ~/.vst3
make clap install-clap FX=basspreamp   # or CLAP, into ~/.clap
```

Leave out `FX=…` to build and install every effect. The install targets replace only this repository's own bundles; anything else in `~/.lv2`, `~/.vst3` or `~/.clap` is left alone. The LV2 build prints "bad port property" messages. They are harmless.

## 2. Let REAPER find the plugins

1. Open *Options → Preferences → Plug-ins* and choose the page for your format: *LV2*, *VST* or *CLAP*.
2. Check that the folder (`~/.lv2`, `~/.vst3` or `~/.clap`) is in the path list. If not, add it.
3. Click *Re-scan*. REAPER only scans at start-up or on request, so do this even if REAPER was already open.

## 3. Set up the track

1. Create a track and arm it for recording from your instrument input. Choose a mono input.
2. Open the track's FX chain (the *FX* button) and click *Add*.
3. Under *LV2*, *VST3* or *CLAP*, choose the effect by name (for example "BassPreamp") and click *OK*.
4. Leave the track's channel count at 2 (the default). The effects are mono. REAPER feeds a mono plugin channel 1 and sends its output to channels 1 and 2. If you are using a stereo source, open *Pin Connector* in the plugin window and route the channel you want to input 1.
5. Turn on input monitoring, or record-monitor, to hear the effect while you play.

If an LV2 plugin doesn't appear, run `jalv urn:pedalkit/<name>` (for example `jalv urn:pedalkit/basspreamp`) in a terminal. If that loads, the bundle is fine and the problem is REAPER's scan.

## 4. Set the input level

The models treat 0 dBFS as 1 V peak at the circuit input, so your interface gain decides how hard the drive controls hit the clipping stages.

1. Set the interface gain so that your loudest notes peak around −12 dBFS on REAPER's meter before the plugin.
2. Start from the effect's defaults, or from its suggested starting settings (see the effect's page, for example [BassPreamp](../basspreamp/index.md#starting-settings)). If the drive consistently sounds too clean or too dirty, adjust the interface gain, not the plugin constants.

Every effect ends in a safety limiter, so the output never exceeds 0 dBFS. If it sounds squashed, lower the effect's output level control.

## 5. Latency

Effects that oversample report a fixed latency, which REAPER compensates for automatically during playback: 32 samples (0.67 ms at 48 kHz) for BassDrive and 64 samples (1.3 ms) for BassPreamp. The [effects table](../effects/index.md) lists every effect's latency. While monitoring through the plugin, you hear that delay on top of the audio buffer. Use a smaller buffer in *Options → Preferences → Audio → Device* to reduce the total.

## 6. Presets and saving your settings

Effects that ship factory presets list them in the preset box at the top of the plugin window. BassPreamp, for example, has "Clean DI", "Growl" and "Grind", loudness-matched so that you can switch between them without a jump in level; its page lists [every preset's settings](../basspreamp/index.md#presets). The presets are built into the LV2 bundle, so choose the LV2 version to get them.

Save your own settings as an FX preset with the *+* button next to the preset box. Or save the chain as a track template (*Track → Save tracks as track template…*).

## What to check by listening

The effects are judged by measurement, not by ear. Each effect's page has a *What to tune by ear* section naming the controls and constants a listener should check, for example [BassPreamp's](../basspreamp/index.md#what-to-tune-by-ear).
