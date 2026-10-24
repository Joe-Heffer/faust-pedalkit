# Using BassPreamp in REAPER (Linux)

This guide takes you from a built plugin to a bass track in REAPER. It assumes a mono bass input, such as a DI or an instrument input on your interface.

## 1. Build and install

```sh
make lv2 lint test FX=basspreamp   # build, lint and run the offline tests
make install FX=basspreamp         # copies build/basspreamp.lv2 to ~/.lv2
```

`make install` replaces only `~/.lv2/basspreamp.lv2`. Other bundles in `~/.lv2` are left alone. The build prints "bad port property" messages. They are harmless.

## 2. Let REAPER find the plugin

1. Open *Options → Preferences → Plug-ins → LV2*.
2. Check that `~/.lv2` is in the path list. If not, add it.
3. Click *Re-scan* (REAPER only scans at start-up or on request, so do this even if REAPER was already open).

## 3. Set up the track

1. Create a track and arm it for recording from your bass input. Choose a mono input.
2. Open the track's FX chain (the *FX* button) and click *Add*.
3. Under *LV2*, choose "BassPreamp" and click *OK*.
4. Set the track's channel count to 2 (the default). The plugin is mono. REAPER feeds it channel 1 and sends its output to channels 1 and 2. If you are using a stereo source, open *Pin Connector* in the plugin window and route the channel you want to input 1.
5. Turn on input monitoring, or record-monitor, to hear the effect while you play.

If the plugin doesn't appear, run `jalv urn:pedalkit/basspreamp` in a terminal. If that loads, the bundle is fine and the problem is REAPER's scan.

## 4. Set the input level

The plugin treats 0 dBFS as 1 V peak at the circuit input, so interface gain decides how hard Drive hits the clipping stages.

1. Set the interface gain so that your loudest notes peak around −12 dBFS on REAPER's meter before the plugin.
2. Start with the settings below. Adjust the interface gain, not the plugin constants, if Drive sounds consistently too clean or too dirty.

## 5. Starting settings

| Control | Start at | Notes |
|---|---|---|
| Level | 0 dB | Unity gain at Blend 0 with a flat EQ |
| Blend | 50 % | 0 is clean only, 100 is preamp only |
| Drive | 50 % | Light, odd-order breakup. Raise it for grit |
| Presence | 50 % | Adds bite ahead of the clipping, so it also affects the distortion |
| Bass, Mid, Treble | 0 dB | Flat |
| Bass Shift | off | Turn on for a 40 Hz shelf, for 5- and 6-string basses |
| Mid Shift | off | Turn on to move the mid band from 500 Hz to 1 kHz |

Tips:

- For a clean low end with some grit on top, keep Blend around 30–50 % and raise Drive.
- If the sound goes hollow in the top end around 2.5 kHz at mid Blend and high Drive, the clean and driven paths are cancelling. This is a property of the modelled blend circuit. Move Blend or reduce Drive.
- The output never exceeds −0.1 dBFS, because of the built-in safety limiter. If it sounds squashed, lower Level.

## 6. Latency

The plugin reports 64 samples of latency (about 1.3 ms at 48 kHz) because of its 4x oversampling. REAPER compensates automatically for playback. While monitoring through the plugin, you hear that delay. Use a smaller audio buffer in *Options → Preferences → Audio → Device* to reduce the total.

## 7. Saving your settings

Save the settings as an FX preset with the *+* button next to the preset box. Or save the chain as a track template (*Track → Save tracks as track template…*).

## What to check by listening

I can only judge the plugin by measurement. These are the things a human ear needs to verify (see the README for the constants to change):

- Whether Drive 50 % is at the right level for your bass and interface gain.
- The clipping character (`railN`, `vos` in `src/basspreamp.dsp`).
- The loudness match between the clean and driven paths (`drvTrim`).
- The EQ shapes (`midQ`, `trebF`).
