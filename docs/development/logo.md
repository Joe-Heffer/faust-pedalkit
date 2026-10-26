# Logo

![Pedal Kit logo](../assets/logo-wordmark.svg){ width="360" }

The mark is a pedal seen from above with a waveform running through it: a clean sine goes in on the left and comes out clipped on the right, which is what most effects in the kit do to a signal. The wordmark is set in Shrikhand, a warm, swashy 1960s-style italic, for a vintage amp-badge feel.

## Files

All in `docs/assets/`, and licensed CC-BY-4.0 like the rest of the documentation.

| File | Use |
|---|---|
| `logo.svg`, `logo.png` (512 px) | Square mark |
| `logo-wordmark.svg` | Mark plus "Pedal Kit"; the text colour follows the light or dark colour scheme |
| `favicon.svg`, `favicon.png` (32 px) | Simplified mark for browser tabs; also used by the site and the browser demo |

## Rebuilding

The files are generated, so edit `tools/logo/build.py` rather than the SVGs, then run it:

```sh
tools/logo/build.py
```

It needs `rsvg-convert` for the PNGs, and fetches the font into `build/logo/` on first use. The text is converted to outlines, so nobody needs the font to view the logo. Shrikhand is by Jonny Pinhorn and licensed under the [SIL Open Font Licence 1.1](https://openfontlicense.org/), which allows embedding its outlines.

## Chosen values

The colours (slate `#1f2933` and `#2b3a47`, off-white `#e8edf1`, amber `#f5a524`), the wave shapes and the typeface are design choices, not sourced from anything. The amber matches the site theme's accent colour. Judge them by eye.
