# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""BassGrit's modelled circuit, for tools/schematics/build.py.

The borrowed part is the classic op-amp hard-clipping distortion, whose values
come from a public parts list and schematic (docs/bassgrit/circuit-notes.md,
sources [n]). The drawing is the circuit src/bassgrit.dsp implements: where the
model departs from the published circuit (the input network, the filter
capacitor, the band split, the Low Blend and Level stage), the sheet draws the
model and its note says so. Sheets are numbered and named after the sections of
the circuit notes; sheet 8 is the design notes' band split.
"""

import math
import textwrap

import stages
from kicadsch import Project, expect, hz, rc_hz, val
from stages import CP, JACK, OPAMP, POT, RVAR, C, D, R

NOTE_WIDTH = 130  # characters; the title block starts at 175 mm


def note(s, lines):
    """The sheet's note, with each paragraph wrapped to fit beside the title block."""
    s.note([w for line in lines for w in textwrap.wrap(line, NOTE_WIDTH)])


CAVEAT = "Modelled circuit (src/bassgrit.dsp); departs from the published circuit where noted"


def project():
    p = Project("bassgrit", "BassGrit", hardware="Pro Co RAT", date="2026-10-26", caveat=CAVEAT)
    sup = stages.supply(
        p,
        [
            "The model has no supply: the input and output buffers are not modelled (circuit notes, section 2).",
            "A 9 V supply and a half-supply bias rail VB are drawn so the op-amp stages can be wired (all chosen).",
            "The published circuit's own half-supply rail is two 100 kOhm resistors and 1 uF [6]; this one is chosen.",
        ],
    )
    inp = input_coupling(p)
    gain = gain_stage(p)
    clip = diodes(p)
    flt = filt(p)
    lvl = level(p)
    split = band_split(p)
    root(p, sup, inp, split, gain, clip, flt, lvl)
    return p


def root(p, sup, inp, split, gain, clip, flt, lvl):
    s = p.root
    s.heading("BassGrit: modelled circuit")
    s.text(
        [
            "Block diagram of section 2 of docs/bassgrit/circuit-notes.md, plus the band split and Low Blend of the design notes.",
            "One sub-sheet per modelled stage, numbered and named after the section that describes it. The input and output",
            "buffers are not modelled. The split (sheet 8) sends only the upper band through the gain stage and the diodes.",
        ],
        (25.4, 43.18),
    )
    p.block(sup, (40.64, 134.62), (38.1, 15.24))
    y1, y2 = 60.96, 106.68
    b3 = p.block(inp, (40.64, y1))
    b8 = p.block(split, (91.44, y1))
    b4 = p.block(gain, (142.24, y1))
    b5 = p.block(clip, (193.04, y1))
    b6 = p.block(flt, (40.64, y2))
    b7 = p.block(lvl, (91.44, y2))

    j1 = s.part(JACK, "JX1", "Input", "inferred", "-", (25.4, 66.04), fields="above", mirror="x")
    s.wire(j1["T"], b3["IN"])
    s.wire(j1["S"], (33.02, j1["S"][1]), (33.02, 73.66))
    s.gnd((33.02, 73.66))
    s.wire(b3["OUT"], b8["IN"])
    s.wire(b8["HIGH"], b4["IN"])
    s.wire(b4["OUT"], b5["IN"])

    # Two long hops are made with global labels rather than wires.
    xo = b5["OUT"][0] + 5.08
    s.wire(b5["OUT"], (xo, b5["OUT"][1]))
    s.glabel("DIODES", (xo, b5["OUT"][1]), 0)
    s.glabel("DIODES", (33.02, b6["IN"][1]), 180)
    s.wire((33.02, b6["IN"][1]), b6["IN"])
    s.wire(b6["OUT"], b7["DRIVEN"])
    xl = b8["LOW"][0] + 5.08
    s.wire(b8["LOW"], (xl, b8["LOW"][1]))
    s.glabel("LOW", (xl, b8["LOW"][1]), 0)
    s.glabel("LOW", (83.82, b7["CLEAN"][1]), 180)
    s.wire((83.82, b7["CLEAN"][1]), b7["CLEAN"])

    j2 = s.part(JACK, "JX2", "Output", "inferred", "-", (154.94, 111.76), rot=180, fields="above")
    s.wire(b7["OUT"], j2["T"])
    s.wire(j2["S"], (147.32, j2["S"][1]), (147.32, 119.38))
    s.gnd((147.32, 119.38))
    s.text(
        [
            "In the DSP the clean path is delayed by 32 samples to line up with the",
            "4x oversampler; that delay has no circuit counterpart (design notes).",
        ],
        (91.44, 147.32),
    )


def input_coupling(p):
    s = p.sheet(3, "Input coupling", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("3 Input coupling (as modelled)")
    s.hlabel("IN", (38.1, 76.2), 180)
    c = s.part(CP, "CX2", "1u", "chosen", "-", (50.8, 76.2), rot=90, fields="above")
    r = s.part(R, "RX3", "33k", "chosen", "-", (68.58, 83.82), fields="right")
    s.wire((38.1, 76.2), c["1"])
    s.wire(c["2"], (68.58, 76.2), r["1"])
    s.wire(r["2"], (68.58, 91.44))
    s.glabel("VB", (68.58, 91.44), 270)
    s.wire((68.58, 76.2), (91.44, 76.2))
    s.hlabel("OUT", (91.44, 76.2))
    f = expect("DC blocker (5 Hz)", rc_hz("33k", "1u"), 5.0)
    f_pedal = expect("pedal input high-pass", rc_hz("1M", "22n"), 7.2, rel=0.01)
    s.text(f"CX2 with RX3: {hz(f)}", (47.0, 104.14))
    note(
        s,
        [
            "Section 3 of the circuit notes. The DSP replaces the pedal's input network with a 5 Hz DC blocker, fi.dcblockerat(5) (chosen):",
            f"CX2 and RX3 stand in for it. The pedal has C1 22 nF with R2 1 MOhm to the bias rail, {hz(f_pedal)} [6] (reported),",
            "R1 1 MOhm across the input, and R4 1 kOhm with C4 1 nF as a radio-frequency low-pass [6]. None of those is modelled.",
        ],
    )
    return s


def gain_stage(p):
    s = p.sheet(4, "Gain stage", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("4 Gain stage")
    u = s.part(OPAMP, "UX1", "LM308", "reported", "[6]", (116.84, 76.2), fields="upright")
    s.opamp_power(u)
    s.hlabel("IN", (63.5, 73.66), 180)
    s.wire((63.5, 73.66), u["+"])
    # Zg: two RC legs from the inverting input to ground.
    inv = (u["-"][0] - 6.35, u["-"][1])
    rb = s.part(R, "R3", "560", "reported", "[6]", (76.2, 88.9), fields="left")
    cb = s.part(CP, "C2", "4u7", "reported", "[6]", (76.2, 100.33), fields="left")
    ra = s.part(R, "R5", "47", "reported", "[6]", (88.9, 88.9), fields="right")
    ca = s.part(CP, "C3", "2u2", "reported", "[6]", (88.9, 100.33), fields="right")
    s.wire(u["-"], inv, (inv[0], 78.74), (76.2, 78.74), rb["1"])
    s.wire((88.9, 78.74), ra["1"])
    s.wire(rb["2"], cb["1"])
    s.wire(ra["2"], ca["1"])
    for part in (cb, ca):
        g = (part["2"][0], 110.49)
        s.wire(part["2"], g)
        s.gnd(g)
    # Zf: the Distortion pot (a rheostat) in parallel with C5.
    c5 = s.part(C, "C5", "100p", "reported", "[6]", (110.49, 111.76), rot=90, fields="below")
    rv = s.part(
        RVAR,
        "RVX1",
        "100k log (Distortion)",
        "reported",
        "[6]",
        (110.49, 127),
        rot=90,
        fields="below",
    )
    left, right = inv[0], u["5"][0] + 6.35
    s.wire((left, 78.74), (left, 127), rv["1"])
    s.wire((left, 111.76), c5["1"])
    s.wire(c5["2"], (right, 111.76))
    s.wire(rv["2"], (right, 127), (right, 76.2))
    s.wire(u["5"], (right, 76.2), (right + 12.7, 76.2))
    s.hlabel("OUT", (right + 12.7, 76.2))

    f_a = expect("leg A corner (fcA)", rc_hz("47", "2.2u"), 1540, rel=0.01)
    f_b = expect("leg B corner (fcB)", rc_hz("560", "4.7u"), 60.5, rel=0.01)
    r_par = 1 / (1 / val("47") + 1 / val("560"))
    g_hf = expect(
        "gain at full Distortion (high frequency)", 1 + val("100k") / r_par, 2300, rel=0.01
    )
    f_fb = expect("feedback pole at full Distortion", rc_hz("100k", "100p"), 16e3, rel=0.01)
    s.text(
        [
            f"R5 with C3: {hz(f_a)}; R3 with C2: {hz(f_b)}",
            f"G = 1 + Rf/(R5 || R3) = {g_hf:.0f} ({20 * math.log10(g_hf):.0f} dB) at full Distortion",
            f"C5 with Rf = 100 kOhm: {hz(f_fb)}",
        ],
        (40.64, 149.86),
    )
    note(
        s,
        [
            "Section 4 of the circuit notes: a non-inverting stage, G = 1 + Zf/Zg. Every value is reported [6]; the wiring is read from its schematic.",
            "UX1: modelled as an ideal op-amp plus a gain-bandwidth pole (GBW = 1 MHz, inferred; see the notes). The pedal also has C6 30 pF",
            "from the LM308's compensation pins [6]; the stock symbol has no such pins, so it is not drawn and is accounted for in GBW.",
            "RVX1: the A100K Distortion pot [6], wired as a rheostat. The log law, about 9 % at noon, is chosen (no source gives the taper).",
            "In the pedal the legs return to ground and the + input is biased to half supply through R2 [6]; here the bias is the rail VB.",
        ],
    )
    return s


def diodes(p):
    s = p.sheet(5, "Diodes", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("5 The diodes")
    s.hlabel("IN", (45.72, 76.2), 180)
    c7 = s.part(CP, "C7", "4u7", "reported", "[6]", (58.42, 76.2), rot=90, fields="above")
    r6 = s.part(R, "R6", "1k", "reported", "[6]", (78.74, 76.2), rot=90, fields="above")
    s.wire((45.72, 76.2), c7["1"])
    s.wire(c7["2"], r6["1"])
    left, right = r6["2"][0] + 5.08, r6["2"][0] + 31.75
    s.wire(r6["2"], (left, 76.2))
    y = 86.36
    d1 = s.part(D, "D1", "1N914", "reported", "[6]", ((left + right) / 2, y), fields="below")
    d2 = s.part(
        D,
        "D2",
        "1N914",
        "reported",
        "[6]",
        ((left + right) / 2, y + 15.24),
        rot=180,
        fields="below",
    )
    s.wire((left, 76.2), (left, y + 15.24))
    for part, a, b in ((d1, "K", "A"), (d2, "A", "K")):
        yy = part[a][1]
        s.wire((left, yy), part[a])
        s.wire(part[b], (right, yy))
    s.wire((right, y), (right, y + 15.24), (right, y + 25.4))
    s.gnd((right, y + 25.4))
    s.wire((left, 76.2), (right + 12.7, 76.2))
    s.hlabel("OUT", (right + 12.7, 76.2))
    s.text(f"C7 with R6 while the diodes conduct: {hz(rc_hz('1k', '4u7'))}", (45.72, 127))
    note(
        s,
        [
            "Section 5 of the circuit notes. The diodes clip to ground after a series resistor, not in the feedback loop [1], [6]. D1, D2 and R6 are reported [6]",
            "(R6 is the 1 kOhm between the coupling capacitor and the diodes in the schematic). The DSP models the pair as a memoryless soft-knee",
            "limit at 0.6 V (pk.kneeClip(0.6, 4), run at 4x; the level is inferred from silicon diodes, the hardness is chosen) and has no R6.",
            "C7 is the pedal's coupling capacitor [6]. The DSP has no DC, so it has no counterpart; its level-dependent corner is an open question.",
        ],
    )
    return s


def filt(p):
    s = p.sheet(6, "Filter", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("6 Filter")
    s.hlabel("IN", (45.72, 76.2), 180)
    r7 = s.part(R, "R7", "1k5", "reported", "[6]", (58.42, 76.2), rot=90, fields="above")
    rf = s.part(
        RVAR, "RVX2", "100k log (Filter)", "reported", "[6]", (76.2, 76.2), rot=90, fields="above"
    )
    c8 = s.part(C, "C8", "4n7", "chosen", "-", (91.44, 88.9), fields="right")
    s.wire((45.72, 76.2), r7["1"])
    s.wire(r7["2"], rf["1"])
    s.wire(rf["2"], (91.44, 76.2), c8["1"])
    s.wire(c8["2"], (91.44, 99.06))
    s.gnd((91.44, 99.06))
    # The pedal's output coupling, which also re-biases the signal for the next sheet.
    c9 = s.part(C, "C9", "22n", "reported", "[6]", (109.22, 76.2), rot=90, fields="above")
    r8 = s.part(R, "R8", "1M", "reported", "[6]", (124.46, 88.9), fields="right")
    s.wire((91.44, 76.2), c9["1"])
    s.wire(c9["2"], (124.46, 76.2), r8["1"])
    s.wire(r8["2"], (124.46, 99.06))
    s.glabel("VB", (124.46, 99.06), 270)
    s.wire((124.46, 76.2), (144.78, 76.2))
    s.hlabel("OUT", (144.78, 76.2))

    f_lo = expect("filter, pot at 100 k", rc_hz(val("1k5") + val("100k"), "4n7"), 334, rel=0.01)
    f_hi = expect("filter, pot at 0", rc_hz("1k5", "4n7"), 22.6e3, rel=0.01)
    p_lo = expect(
        "pedal filter, pot at 100 k", rc_hz(val("1k5") + val("100k"), "3n3"), 475, rel=0.01
    )
    p_hi = expect("pedal filter, pot at 0", rc_hz("1k5", "3n3"), 32.1e3, rel=0.01)
    f_out = expect("output coupling (not modelled)", rc_hz("1M", "22n"), 7.2, rel=0.01)
    s.text(
        [
            f"R7 + RVX2 with C8: {hz(f_hi)} (Filter 0) to {hz(f_lo)} (Filter 100)",
            f"with the pedal's 3.3 nF: {hz(p_hi)} to {hz(p_lo)}",
        ],
        (45.72, 109.22),
    )
    s.text(f"C9 with R8: {hz(f_out)}", (104.14, 109.22))
    note(
        s,
        [
            "Section 6 of the circuit notes: a first-order passive low-pass, R7 1.5 kOhm [6] and the A100K Filter pot [6] (a rheostat) into a capacitor to ground.",
            "C8 is 4.7 nF here (chosen, for bass); the pedal's is 3.3 nF [6], so the range moves from the values above to 334 Hz to 22.6 kHz.",
            "RVX2 has a log law, as in the DSP (chosen). C9 and R8 are the pedal's output coupling [6], about 0.02 dB at the 120 Hz crossover;",
            "the DSP has no counterpart. The JFET output buffer and the Volume pot that follow are not modelled; the Level stage replaces them.",
        ],
    )
    return s


def level(p):
    s = p.sheet(
        7,
        "Level and Low Blend",
        pins=[("DRIVEN", "input"), ("CLEAN", "input"), ("OUT", "output")],
    )
    s.heading("7 Level and calibration, with Low Blend")
    # Inverting summer: the driven path and the clean path, both at outTrim and the +12 dB make-up.
    u = s.part(OPAMP, "UX2", "OPAMP", "chosen", "-", (93.98, 81.28), fields="upright")
    s.opamp_power(u)
    s.wire(u["+"], (83.82, 78.74), (83.82, 71.12))
    s.glabel("VB", (83.82, 71.12), 90)
    s.hlabel("DRIVEN", (40.64, 83.82), 180)
    rd = s.part(R, "RX7", "10k", "chosen", "-", (60.96, 83.82), rot=90, fields="above")
    s.wire((40.64, 83.82), rd["1"])
    s.wire(rd["2"], (81.28, 83.82), u["-"])
    s.hlabel("CLEAN", (40.64, 101.6), 180)
    blend = s.part(POT, "RVX3", "1k lin (Low Blend)", "chosen", "-", (50.8, 109.22), fields="left")
    s.wire((40.64, 101.6), (50.8, 101.6), blend["1"])
    s.wire(blend["3"], (50.8, 118.11))
    s.glabel("VB", (50.8, 118.11), 270)
    rc = s.part(R, "RX8", "10k", "chosen", "-", (66.04, 109.22), rot=90, fields="below")
    s.wire(blend["2"], rc["1"])
    s.wire(rc["2"], (81.28, 109.22), (81.28, 83.82))
    rf = s.part(R, "RX9", "47k", "chosen", "-", (96.52, 124.46), rot=90, fields="below")
    s.wire((81.28, 109.22), (81.28, 124.46), rf["1"])
    s.wire(rf["2"], (111.76, 124.46), (111.76, 81.28))
    s.wire(u["5"], (111.76, 81.28))
    # Level: the pedal's 100 k audio pot, then an inverting unity buffer.
    lvl = s.part(
        POT, "RVX4", "100k log (Level)", "reported", "[6]", (124.46, 88.9), fields="upright"
    )
    s.wire((111.76, 81.28), (124.46, 81.28), lvl["1"])
    s.wire(lvl["3"], (124.46, 97.79))
    s.glabel("VB", (124.46, 97.79), 270)
    u2 = s.part(OPAMP, "UX3", "OPAMP", "chosen", "-", (162.56, 86.36), fields="upright")
    s.opamp_power(u2)
    s.wire(u2["+"], (152.4, 83.82), (152.4, 76.2))
    s.glabel("VB", (152.4, 76.2), 90)
    ri = s.part(R, "RX10", "1M", "chosen", "-", (139.7, 101.6), rot=90, fields="below")
    s.wire(lvl["2"], (130.81, 88.9), (130.81, 101.6), ri["1"])
    s.wire(ri["2"], (147.32, 101.6), (147.32, 88.9), u2["-"])
    ro = s.part(R, "RX11", "1M", "chosen", "-", (162.56, 111.76), rot=90, fields="below")
    s.wire((147.32, 101.6), (147.32, 111.76), ro["1"])
    s.wire(ro["2"], (177.8, 111.76), (177.8, 86.36))
    s.wire(u2["5"], (177.8, 86.36))
    co = s.part(CP, "CX4", "10u", "chosen", "-", (187.96, 86.36), rot=90, fields="above")
    s.wire((177.8, 86.36), co["1"])
    s.wire(co["2"], (200.66, 86.36))
    s.hlabel("OUT", (200.66, 86.36))

    g = val("47k") / val("10k")
    g_dsp = 1.2 * 10 ** (12 / 20)
    expect("summer gain (outTrim x +12 dB)", g, g_dsp, rel=0.02)
    clean = expect("clean/driven gain ratio at Low Blend 100", val("47k") / val("10k") / g, 1.0)
    s.text(f"driven x{g:.1f} (outTrim 1.2 with +12 dB of make-up)", (30.48, 96.52))
    s.text(f"clean x Low Blend x {clean:g} of the driven gain", (43.18, 129.54))
    note(
        s,
        [
            "Section 7 of the circuit notes and the design notes. Low Blend is BassGrit's addition: the clean lower band, added at Low Blend x the driven gain.",
            "UX2 sums both bands, inverted, at outTrim 1.2 (chosen) with +11.8 dB of make-up for the DSP's Level range of -40 to +12 dB (chosen).",
            "RVX4: the pedal's A100K Volume pot [6]. UX3 inverts back to the input's polarity (chosen). RVX3 is small against RX8 so the Low Blend",
            "law stays linear. The pedal's JFET buffer is replaced by this stage (section 7).",
        ],
    )
    return s


def sallen_key(s, kind, x, yl, refs, values):
    """One unity-gain Sallen-Key section whose input is at (x, yl). kind is
    "lp" (series resistors, capacitor feedback) or "hp" (series capacitors,
    resistor feedback). refs and values: series 1, series 2, feedback,
    ground, op-amp. Returns the output point."""
    n1, n2, nf, ng, nu = refs
    v1, v2, vf, vg, vu = values
    ser_el, fb = (R, C) if kind == "lp" else (C, R)
    # Ground element and series elements: horizontal for series, vertical for ground and feedback.
    a = s.part(ser_el, n1, v1, "chosen", "-", (x + 8.89, yl), rot=90, fields="above")
    b = s.part(ser_el, n2, v2, "chosen", "-", (x + 25.4, yl), rot=90, fields="above")
    u = s.part(OPAMP, nu, vu, "chosen", "-", (x + 63.5, yl + 2.54), fields="upright")
    s.opamp_power(u)
    node = (x + 16.51, yl)
    s.wire((x, yl), a["1"])
    s.wire(a["2"], node, b["1"])
    yfb = yl - 15.24
    f = s.part(fb, nf, vf, "chosen", "-", (x + 29.21, yfb), rot=90, fields="above")
    s.wire(node, (node[0], yfb), (f["1"][0], yfb), f["1"])
    # Ground element from the non-inverting node to the bias rail.
    gx = x + 40.64
    g = s.part(fb if kind == "hp" else C, ng, vg, "chosen", "-", (gx, yl + 7.62), fields="left")
    s.wire(b["2"], (gx, yl), u["+"])
    s.wire((gx, yl), g["1"])
    s.wire(g["2"], (gx, yl + 15.24))
    s.glabel("VB", (gx, yl + 15.24), 270)
    # Follower: the output feeds back to the inverting input and to the feedback element.
    out = u["5"]
    xr = out[0] + 5.08
    s.wire(f["2"], (xr, yfb), (xr, out[1]))
    s.wire(
        u["-"],
        (u["-"][0] - 2.54, u["-"][1]),
        (u["-"][0] - 2.54, yl + 19.05),
        (xr, yl + 19.05),
        (xr, out[1]),
    )
    s.wire(out, (xr, out[1]))
    return (xr, out[1])


def band_split(p):
    s = p.sheet(
        8,
        "Band split",
        pins=[("IN", "input"), ("HIGH", "output"), ("LOW", "output")],
    )
    s.heading("8 Band split (design notes): 4th-order Linkwitz-Riley at Crossover")
    r, c1, c2 = "93k1", "20n", "10n"
    hp_c, hp_rf, hp_rg = "10n", "93k1", "187k"
    yl_lp, yl_hp = 66.04, 127.0
    x0, gap = 50.8, 83.82
    s.hlabel("IN", (30.48, yl_lp), 180)
    s.wire((30.48, yl_lp), (40.64, yl_lp), (40.64, yl_hp), (x0, yl_hp))
    s.wire((40.64, yl_lp), (x0, yl_lp))
    o1 = sallen_key(
        s, "lp", x0, yl_lp, ("RX12", "RX13", "CX5", "CX6", "UX4"), (r, r, c1, c2, "OPAMP")
    )
    o2 = sallen_key(
        s,
        "lp",
        x0 + gap,
        o1[1],
        ("RX14", "RX15", "CX7", "CX8", "UX5"),
        (r, r, c1, c2, "OPAMP"),
    )
    s.wire(o1, (x0 + gap, o1[1]))
    s.wire(o2, (o2[0] + 12.7, o2[1]))
    s.hlabel("LOW", (o2[0] + 12.7, o2[1]))
    h1 = sallen_key(
        s,
        "hp",
        x0,
        yl_hp,
        ("CX9", "CX10", "RX16", "RX17", "UX6"),
        (hp_c, hp_c, hp_rf, hp_rg, "OPAMP"),
    )
    h2 = sallen_key(
        s,
        "hp",
        x0 + gap,
        h1[1],
        ("CX11", "CX12", "RX18", "RX19", "UX7"),
        (hp_c, hp_c, hp_rf, hp_rg, "OPAMP"),
    )
    s.wire(h1, (x0 + gap, h1[1]))
    s.wire(h2, (h2[0] + 12.7, h2[1]))
    s.hlabel("HIGH", (h2[0] + 12.7, h2[1]))

    f_lp = expect(
        "low-pass corner", 1 / (2 * math.pi * val(r) * math.sqrt(val(c1) * val(c2))), 120, rel=0.01
    )
    q_lp = expect("low-pass Q", 0.5 * math.sqrt(val(c1) / val(c2)), 1 / math.sqrt(2), rel=0.005)
    f_hp = expect(
        "high-pass corner",
        1 / (2 * math.pi * val(hp_c) * math.sqrt(val(hp_rf) * val(hp_rg))),
        120,
        rel=0.01,
    )
    q_hp = expect(
        "high-pass Q", 0.5 * math.sqrt(val(hp_rg) / val(hp_rf)), 1 / math.sqrt(2), rel=0.005
    )
    s.text(f"each low-pass section: {hz(f_lp)}, Q = {q_lp:.3f}", (x0, yl_lp + 24.0))
    s.text(f"each high-pass section: {hz(f_hp)}, Q = {q_hp:.3f}", (x0, yl_hp + 24.0))
    note(
        s,
        [
            "Not part of the published circuit: the design notes' split. The DSP uses two Butterworth sections per side (fi.lowpass(2) twice, fi.highpass(2) twice),",
            "a 4th-order Linkwitz-Riley pair, so the bands are in phase at Crossover and sum to an all-pass. There is no circuit behind it:",
            "this is a standard analogue stand-in, all chosen. Each section is a unity-gain Sallen-Key with Q = 0.707 and a fixed 120 Hz corner",
            "(the DSP's default); the Crossover control would move all four corners together, which is not drawn.",
        ],
    )
    return s
