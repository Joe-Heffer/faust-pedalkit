# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""MidHump's modelled circuit, for tools/schematics/build.py.

The borrowed part is the classic green mid-hump overdrive, whose values come
from public analyses (docs/midhump/circuit-notes.md, sources [n]). The
drawing is the circuit src/midhump.dsp implements: where the model departs
from the published circuit (the tone stage, the Blend control, the Level
range), the sheet draws the model and its note says so. Sheets are numbered
and named after the sections of the circuit notes.
"""

import math

import stages
from kicadsch import Project, expect, hz, rc_hz, val
from stages import CP, JACK, OPAMP, POT, RVAR, C, D, R

CAVEAT = "Modelled circuit (src/midhump.dsp); departs from the published circuit where noted"


def project():
    p = Project(
        "midhump", "MidHump", hardware="Ibanez TS808 / TS9", date="2026-10-26", caveat=CAVEAT
    )
    sup = stages.supply(
        p,
        [
            "The model has no supply: the input and output buffers are not modelled (circuit notes, section 2).",
            "A 9 V supply and a half-supply bias rail VB are drawn so the op-amp stages can be wired (all chosen).",
        ],
    )
    root(p, sup, input_coupling(p), clipping(p), passive(p), tone(p), level(p))
    return p


def root(p, sup, inp, clip, lp, tn, lvl):
    s = p.root
    s.heading("MidHump: modelled circuit")
    s.text(
        [
            "Block diagram of section 2 of docs/midhump/circuit-notes.md, plus the Blend control of the design notes.",
            "One sub-sheet per modelled stage, numbered and named after the section that describes it. The input",
            "and output buffers are not modelled. Blend at 0 is the published circuit.",
        ],
        (25.4, 43.18),
    )
    p.block(sup, (40.64, 134.62), (38.1, 15.24))
    y1, y2 = 60.96, 106.68
    b3 = p.block(inp, (40.64, y1))
    b4 = p.block(clip, (91.44, y1))
    b6 = p.block(lp, (142.24, y1))
    b7 = p.block(tn, (193.04, y1))
    b8 = p.block(lvl, (40.64, y2))

    j1 = s.part(JACK, "JX1", "Input", "inferred", "-", (25.4, 66.04), fields="above", mirror="x")
    s.wire(j1["T"], b3["IN"])
    s.wire(j1["S"], (33.02, j1["S"][1]), (33.02, 73.66))
    s.gnd((33.02, 73.66))
    s.wire(b3["OUT"], b4["IN"])
    s.wire(b4["OUT"], b6["IN"])
    s.wire(b6["OUT"], b7["IN"])

    jx = b3["OUT"][0] + 6.35
    s.wire((jx, b3["OUT"][1]), (jx, 91.44), (33.02, 91.44), (33.02, b8["CLEAN"][1]), b8["CLEAN"])
    s.wire(b7["OUT"], (b7["OUT"][0] + 5.08, b7["OUT"][1]), (b7["OUT"][0] + 5.08, 96.52))
    s.wire((b7["OUT"][0] + 5.08, 96.52), (35.56, 96.52), (35.56, b8["DRIVEN"][1]), b8["DRIVEN"])

    j2 = s.part(JACK, "JX2", "Output", "inferred", "-", (104.14, 111.76), rot=180, fields="above")
    s.wire(b8["OUT"], j2["T"])
    s.wire(j2["S"], (96.52, j2["S"][1]), (96.52, 119.38))
    s.gnd((96.52, 119.38))
    s.text("clean (Blend)", (jx + 1.27, 90.17))
    s.text("driven", (200.66, 95.25))
    s.text(
        [
            "In the DSP the clean path is delayed by 32 samples to line up with the",
            "4x oversampler; that delay has no circuit counterpart (design notes).",
        ],
        (91.44, 147.32),
    )


def input_coupling(p):
    s = p.sheet(3, "Input coupling", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("3 Input coupling")
    s.hlabel("IN", (38.1, 76.2), 180)
    c = s.part(C, "CX2", "20n", "inferred", "-", (48.26, 76.2), rot=90, fields="above")
    r = s.part(R, "RX3", "510k", "reported", "[2]", (66.04, 83.82), fields="right")
    s.wire((38.1, 76.2), c["1"])
    s.wire(c["2"], (66.04, 76.2), r["1"])
    s.wire(r["2"], (66.04, 91.44))
    s.glabel("VB", (66.04, 91.44), 270)
    s.wire((66.04, 76.2), (88.9, 76.2))
    s.hlabel("OUT", (88.9, 76.2))
    f = expect("input high-pass (fcIn)", rc_hz("510k", "20n"), 15.6, rel=0.01)
    s.text(f"CX2 with RX3: {hz(f)}", (45.72, 104.14))
    s.note(
        [
            "Section 3 of the circuit notes. RX3: the 510 kOhm bias resistor that sets the input impedance (reported [2]).",
            "CX2: 20 nF, recalled from the standard schematic and not sourced (inferred). Together: fcIn, about 15.6 Hz.",
            "The buffer after this, and its 1 uF coupling into the clipping stage [2], are not modelled.",
        ]
    )
    return s


def clipping(p):
    s = p.sheet(4, "Clipping stage", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("4 Clipping stage and 5 The diodes")
    u = s.part(OPAMP, "UX1", "OPAMP", "reported", "[1], [2]", (106.68, 76.2), fields="upright")
    s.opamp_power(u)
    s.hlabel("IN", (63.5, 73.66), 180)
    s.wire((63.5, 73.66), u["+"])
    # Grounded leg Zg: R4 in series with C3.
    r4 = s.part(R, "R4", "4.7k", "reported", "[2]", (76.2, 86.36), fields="left")
    c3 = s.part(C, "C3", "47n", "reported", "[2]", (76.2, 97.79), fields="left")
    s.wire(u["-"], (93.98, 78.74), (76.2, 78.74), r4["1"])
    s.wire(r4["2"], c3["1"])
    s.wire(c3["2"], (76.2, 106.68))
    s.glabel("VB", (76.2, 106.68), 270)
    # Feedback Zf: R6 plus the Drive pot, in parallel with C4 and the diodes.
    c4 = s.part(C, "C4", "51p", "reported", "[2]", (110.49, 96.52), rot=90, fields="below")
    d1 = s.part(D, "DX1", "silicon", "reported", "[3]", (110.49, 111.76), fields="below")
    d2 = s.part(D, "DX2", "silicon", "reported", "[3]", (110.49, 127), rot=180, fields="below")
    r6 = s.part(R, "R6", "51k", "reported", "[2]", (101.6, 144.78), rot=90, fields="below")
    rv = s.part(
        RVAR, "RVX1", "500k log (Drive)", "chosen", "[2]", (116.84, 144.78), rot=90, fields="below"
    )
    left, right = 93.98, 127.0
    s.wire((left, 78.74), (left, 144.78), r6["1"])
    s.wire(r6["2"], rv["1"])
    s.wire(rv["2"], (right, 144.78), (right, 76.2))
    for part, a, b in ((c4, "1", "2"), (d1, "K", "A"), (d2, "A", "K")):
        y = part[a][1]
        s.wire((left, y), part[a])
        s.wire(part[b], (right, y))
    s.wire(u["5"], (right, 76.2), (139.7, 76.2))
    s.hlabel("OUT", (139.7, 76.2))

    f_hp = expect("R4, C3 corner", rc_hz("4.7k", "47n"), 720, rel=0.01)
    rf0, rf1 = val("51k"), val("51k") + val("500k")
    f0 = expect("C4 corner at Drive 0", rc_hz(rf0, "51p"), 61e3, rel=0.01)
    f1 = expect("C4 corner at Drive 100", rc_hz(rf1, "51p"), 5.7e3, rel=0.01)
    g0 = expect("gain at Drive 0", 1 + rf0 / val("4.7k"), 11.9, rel=0.01)
    g1 = expect("gain at Drive 100", 1 + rf1 / val("4.7k"), 118, rel=0.01)
    s.text([f"R4 with C3: {hz(f_hp)}", "bass passes at unity below it"], (38.1, 116.84))
    s.text(
        [
            f"C4 with Rf: {hz(f0)} (Drive 0)",
            f"to {hz(f1)} (Drive 100)",
            f"G = 1 + Rf/R4 = {g0:.1f} to {g1:.0f}",
            "Rf = R6 + RVX1",
        ],
        (132.08, 104.14),
    )
    s.note(
        [
            "Sections 4 and 5 of the circuit notes: a non-inverting stage, G = 1 + Zf/Zg, values confirmed in [2].",
            "UX1: modelled as an ideal op-amp. DX1, DX2: two silicon diodes in anti-parallel across the feedback [3];",
            "the DSP limits the feedback branch voltage with a soft knee at 0.6 V (Vd reported [2], knee shape chosen).",
            "RVX1: the 500 kOhm Drive pot [2] with a log law, about 9 % at noon (chosen; no source gives the taper).",
            "In the DSP the C4 low-pass comes before the diodes; in this circuit they share a node (section 5).",
        ]
    )
    return s


def passive(p):
    s = p.sheet(6, "Passive low-pass", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("6 Passive low-pass")
    s.hlabel("IN", (50.8, 76.2), 180)
    r7 = s.part(R, "R7", "1k", "reported", "[1], [2]", (66.04, 76.2), rot=90, fields="above")
    c5 = s.part(C, "C5", "220n", "reported", "[1], [2]", (78.74, 83.82), fields="right")
    s.wire((50.8, 76.2), r7["1"])
    s.wire(r7["2"], (78.74, 76.2), c5["1"])
    s.wire(c5["2"], (78.74, 91.44))
    s.glabel("VB", (78.74, 91.44), 270)
    s.wire((78.74, 76.2), (101.6, 76.2))
    s.hlabel("OUT", (101.6, 76.2))
    f = expect("passive low-pass", rc_hz("1k", "220n"), 723, rel=0.01)
    s.text(f"R7 with C5: {hz(f)}", (60.96, 104.14))
    s.note(
        [
            "Section 6 of the circuit notes. R7 and C5 form a first-order low-pass at 723 Hz after the clipping stage",
            "(reported [1], [2]). C5 returns to the bias rail VB, the stage's AC ground.",
        ]
    )
    return s


def tone(p):
    s = p.sheet(7, "Tone stage", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("7 Tone stage (as modelled)")
    u = s.part(OPAMP, "UX2", "OPAMP", "chosen", "-", (93.98, 76.2), fields="upright")
    s.opamp_power(u)
    s.hlabel("IN", (55.88, 73.66), 180)
    s.wire((55.88, 73.66), u["+"])
    rg = s.part(R, "RX4", "220", "inferred", "[1], [5]", (73.66, 86.36), fields="left")
    cg = s.part(C, "CX3", "220n", "inferred", "[1], [5]", (73.66, 97.79), fields="left")
    s.wire(u["-"], (81.28, 78.74), (73.66, 78.74), rg["1"])
    s.wire(rg["2"], cg["1"])
    s.wire(cg["2"], (73.66, 106.68))
    s.glabel("VB", (73.66, 106.68), 270)
    rv = s.part(RVAR, "RVX2", "0-780 (Tone)", "chosen", "-", (96.52, 101.6), rot=90, fields="below")
    s.wire((81.28, 78.74), (81.28, 101.6), rv["1"])
    s.wire(rv["2"], (111.76, 101.6), (111.76, 76.2))
    s.wire(u["5"], (111.76, 76.2))
    # The DSP's 5 Hz DC blocker after the shelf.
    cd = s.part(C, "CX4", "1u", "chosen", "-", (124.46, 76.2), rot=90, fields="above")
    rd = s.part(R, "RX5", "33k", "chosen", "-", (134.62, 83.82), fields="right")
    s.wire((111.76, 76.2), cd["1"])
    s.wire(cd["2"], (134.62, 76.2), rd["1"])
    s.wire(rd["2"], (134.62, 91.44))
    s.glabel("VB", (134.62, 91.44), 270)
    s.wire((134.62, 76.2), (152.4, 76.2))
    s.hlabel("OUT", (152.4, 76.2))

    fp = expect("shelf pole (fcShelf)", rc_hz("220", "220n"), 3290, rel=0.01)
    fz = expect(
        "shelf zero at Tone 100 (fcPassive)", rc_hz(val("220") + 780, "220n"), 723, rel=0.01
    )
    fdc = expect("DC blocker", rc_hz("33k", "1u"), 5.0)
    s.text(
        [
            f"pole RX4 with CX3: {hz(fp)}",
            f"zero (RX4 + RVX2) with CX3: {hz(fp)} (Tone 0)",
            f"to {hz(fz)} (Tone 100)",
        ],
        (38.1, 121.92),
    )
    s.text(f"CX4 with RX5: {hz(fdc)}", (119.38, 104.14))
    s.note(
        [
            "Section 7 of the circuit notes. This is the shelf the DSP implements, H = (1 + s/wz)/(1 + s/wp), not the pedal's",
            "tone network: [2] describes a 20 kOhm pot between the op-amp inputs with 220 Ohm and 220 nF from its wiper to ground.",
            "RX4, CX3: the reported 220 Ohm and 220 nF [1], [5], used here for the fixed 3.29 kHz pole (inferred).",
            "RVX2: moves the zero from 3.29 kHz to 723 Hz; its law, 220 (4.55^Tone - 1) Ohm, gives the DSP's log sweep (chosen).",
            "CX4, RX5: the 5 Hz DC blocker after the shelf (chosen). Solving [2]'s network is the first open question.",
        ]
    )
    return s


def level(p):
    s = p.sheet(
        8,
        "Level and calibration",
        pins=[("DRIVEN", "input"), ("CLEAN", "input"), ("OUT", "output")],
    )
    s.heading("8 Level and calibration, with Blend")
    # Inverting summer: the driven path at x3.9 and the clean path at Blend x 1.95.
    u = s.part(OPAMP, "UX3", "OPAMP", "chosen", "-", (93.98, 81.28), fields="upright")
    s.opamp_power(u)
    s.wire(u["+"], (83.82, 78.74), (83.82, 71.12))
    s.glabel("VB", (83.82, 71.12), 90)
    s.hlabel("DRIVEN", (40.64, 83.82), 180)
    rd = s.part(R, "RX6", "10k", "chosen", "-", (60.96, 83.82), rot=90, fields="above")
    s.wire((40.64, 83.82), rd["1"])
    s.wire(rd["2"], (81.28, 83.82), u["-"])
    s.hlabel("CLEAN", (40.64, 101.6), 180)
    blend = s.part(POT, "RVX3", "1k lin (Blend)", "chosen", "-", (50.8, 109.22), fields="left")
    s.wire((40.64, 101.6), (50.8, 101.6), blend["1"])
    s.wire(blend["3"], (50.8, 118.11))
    s.glabel("VB", (50.8, 118.11), 270)
    rc = s.part(R, "RX7", "20k", "chosen", "-", (66.04, 109.22), rot=90, fields="below")
    s.wire(blend["2"], rc["1"])
    s.wire(rc["2"], (81.28, 109.22), (81.28, 83.82))
    rf = s.part(R, "RX8", "39k", "chosen", "-", (96.52, 124.46), rot=90, fields="below")
    s.wire((81.28, 109.22), (81.28, 124.46), rf["1"])
    s.wire(rf["2"], (111.76, 124.46), (111.76, 81.28))
    s.wire(u["5"], (111.76, 81.28))
    # Level: the pedal's 100 k audio pot, then an inverting unity buffer.
    lvl = s.part(
        POT, "RVX4", "100k log (Level)", "reported", "[2]", (124.46, 88.9), fields="upright"
    )
    s.wire((111.76, 81.28), (124.46, 81.28), lvl["1"])
    s.wire(lvl["3"], (124.46, 97.79))
    s.glabel("VB", (124.46, 97.79), 270)
    u2 = s.part(OPAMP, "UX4", "OPAMP", "chosen", "-", (162.56, 86.36), fields="upright")
    s.opamp_power(u2)
    s.wire(u2["+"], (152.4, 83.82), (152.4, 76.2))
    s.glabel("VB", (152.4, 76.2), 90)
    ri = s.part(R, "RX9", "1M", "chosen", "-", (139.7, 101.6), rot=90, fields="below")
    s.wire(lvl["2"], (130.81, 88.9), (130.81, 101.6), ri["1"])
    s.wire(ri["2"], (147.32, 101.6), (147.32, 88.9), u2["-"])
    ro = s.part(R, "RX10", "1M", "chosen", "-", (162.56, 111.76), rot=90, fields="below")
    s.wire((147.32, 101.6), (147.32, 111.76), ro["1"])
    s.wire(ro["2"], (177.8, 111.76), (177.8, 86.36))
    s.wire(u2["5"], (177.8, 86.36))
    co = s.part(CP, "CX5", "10u", "chosen", "-", (187.96, 86.36), rot=90, fields="above")
    s.wire((177.8, 86.36), co["1"])
    s.wire(co["2"], (200.66, 86.36))
    s.hlabel("OUT", (200.66, 86.36))

    g = expect("driven gain (dB)", 20 * math.log10(val("39k") / val("10k")), 12, rel=0.02)
    trim = expect("clean/driven gain ratio (cleanTrim)", val("10k") / val("20k"), 0.5, rel=0.01)
    s.text(f"driven x{val('39k') / val('10k'):.1f} (+{g:.1f} dB)", (45.72, 91.44))
    s.text(f"clean x Blend x {trim:g} of the driven gain", (43.18, 129.54))
    s.note(
        [
            "Section 8 of the circuit notes and the design notes. Blend is MidHump's addition: a full-range clean copy of the",
            "input, added at Blend x 0.5 (cleanTrim, chosen). UX3 sums it with the driven path, both inverted, with +11.8 dB",
            "of make-up for the DSP's Level range of -40 to +12 dB (chosen). RVX4: the pedal's 100 kOhm audio volume pot [2].",
            "UX4 inverts back to the input's polarity (chosen). RVX3 is small against RX7 so the Blend law stays linear.",
        ]
    )
    return s
