# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""BassPreamp's modelled circuit, for tools/schematics/build.py.

The drive section and the fixed "speaker" voicing come from a public DIY
trace of the earlier (V1) pedal, source [2] of docs/basspreamp/circuit-notes.md,
whose designators (R3, C16, IC2_C ...) are kept. The V2 EQ has no public
schematic, so sheet 9 is an analogue stand-in for the DSP's filters, all
chosen. Sheets are numbered and named after the sections of the circuit notes.
"""

import math

import stages
from kicadsch import Project, expect, hz, lc_hz, rc_hz, val
from stages import C, JACK, L, OPAMP, POT, RVAR, SW, R, band, series

CAVEAT = "Modelled circuit (src/basspreamp.dsp): V1 trace [2] for the drive and voicing, chosen EQ"
TL = ("TL07x", "reported", "[2]")


def project():
    p = Project(
        "basspreamp",
        "BassPreamp",
        hardware="Tech 21 SansAmp Bass Driver DI",
        date="2026-10-26",
        caveat=CAVEAT,
    )
    sup = stages.supply(
        p,
        [
            "Section 2 of the circuit notes: four TL07x op-amps on a 9 V supply, with a bias rail VB of about 4.7 V",
            "(test voltages: 4.68-4.80 V on 9.32 V, reported [2]). The divider and decoupling values here are chosen.",
        ],
        vb="VB = 4.7 V",
    )
    sheets = [
        sup,
        input_buffer(p),
        pre_drive(p),
        gain_stage(p, 4, "Presence stage"),
        gain_stage(p, 5, "Drive stage"),
        voicing(p),
        blend(p),
        eq(p),
    ]
    root(p, *sheets)
    return p


def root(p, sup, buf, pre, pres, drv, voi, bl, eq_):
    s = p.root
    s.heading("BassPreamp: modelled circuit")
    s.text(
        [
            "Block diagram of section 2 of docs/basspreamp/circuit-notes.md: one sub-sheet per stage, numbered and named",
            "after the section that describes it. Sheets 2 to 8 follow the public trace of the earlier version [2], with its",
            "designators; sheet 9 is a chosen stand-in for the later version's EQ, whose schematic is not public.",
        ],
        (25.4, 43.18),
    )
    size = (33.02, 20.32)
    p.block(sup, (40.64, 134.62), (33.02, 15.24))
    y1, y2 = 60.96, 106.68
    xs = [40.64, 88.9, 137.16, 185.42, 233.68]
    b2, b3, b4, b5, b7 = (p.block(sh, (x, y1), size) for sh, x in zip((buf, pre, pres, drv, voi), xs, strict=True))
    b8 = p.block(bl, (40.64, y2), size)
    b9 = p.block(eq_, (88.9, y2), size)

    j1 = s.part(JACK, "JX1", "Input", "documented", "[1]", (25.4, 66.04), fields="above", mirror="x")
    s.wire(j1["T"], b2["IN"])
    s.wire(j1["S"], (33.02, j1["S"][1]), (33.02, 73.66))
    s.gnd((33.02, 73.66))
    for a, b in ((b2, b3), (b3, b4), (b4, b5), (b5, b7)):
        s.wire(a["OUT"], b["IN"])

    jx = b2["OUT"][0] + 6.35
    s.wire((jx, b2["OUT"][1]), (jx, 91.44), (33.02, 91.44), (33.02, b8["CLEAN"][1]), b8["CLEAN"])
    xo = b7["OUT"][0] + 5.08
    s.wire(b7["OUT"], (xo, b7["OUT"][1]), (xo, 96.52), (35.56, 96.52), (35.56, b8["DRIVEN"][1]), b8["DRIVEN"])
    s.wire(b8["OUT"], b9["IN"])
    j2 = s.part(JACK, "JX2", "Output", "documented", "[1]", (147.32, 111.76), rot=180, fields="above")
    s.wire(b9["OUT"], j2["T"])
    s.wire(j2["S"], (139.7, j2["S"][1]), (139.7, 119.38))
    s.gnd((139.7, 119.38))
    s.text("clean", (jx + 1.27, 90.17))
    s.text("preamp", (250, 95.25))
    s.text(
        [
            "Both clippers run at 4x oversampling in the DSP, so the clean path is delayed by 64 samples to line up;",
            "that delay has no circuit counterpart. The DSP's Cab Bypass switch, which replaces sheet 7 with a fixed",
            "-11 dB trim, is the plugin's addition and is not drawn.",
        ],
        (88.9, 144.78),
    )


def input_buffer(p):
    s = p.sheet(2, "Input buffer", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("2 Input buffer")
    s.hlabel("IN", (38.1, 76.2), 180)
    c = s.part(C, "C1", "22n", "reported", "[2]", (48.26, 76.2), rot=90, fields="above")
    r = s.part(R, "R2", "1M", "reported", "[2]", (66.04, 83.82), fields="left")
    u = s.part(OPAMP, "IC1_D", *TL, (88.9, 78.74), fields="upright")
    s.wire((38.1, 76.2), c["1"])
    s.wire(c["2"], (66.04, 76.2), u["+"])
    s.wire((66.04, 76.2), r["1"])
    s.wire(r["2"], (66.04, 91.44))
    s.glabel("VB", (66.04, 91.44), 270)
    s.opamp_power(u)
    s.wire(u["-"], (81.28, 96.52), (106.68, 96.52), (106.68, 78.74))
    s.wire(u["5"], (121.92, 78.74))
    s.hlabel("OUT", (121.92, 78.74))
    f = expect("C1, R2 corner", rc_hz("1M", "22n"), 7.23, rel=0.01)
    s.text(f"C1 with R2: {hz(f)}", (45.72, 104.14))
    s.text("(DSP: 5 Hz DC blocker; see open questions)", (45.72, 106.68))
    s.note(
        [
            "Section 2 of the circuit notes: C1 22 nF and R2 1 MOhm into the buffer IC1_D, as traced [2].",
            "The output feeds the clean side of the Blend pot (sheet 8) and the pre-drive network (sheet 3).",
        ]
    )
    return s


def pre_drive(p):
    s = p.sheet(3, "Pre-drive network", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("3 Pre-drive network")
    rep = ("reported", "[2]")
    s.hlabel("IN", (38.1, 71.12), 180)
    r3 = s.part(R, "R3", "100k", *rep, (68.58, 71.12), rot=90, fields="above")
    c2 = s.part(C, "C2", "22n", *rep, (50.8, 81.28), fields="left")
    c3 = s.part(C, "C3", "22n", *rep, (86.36, 81.28), fields="right")
    c4 = s.part(C, "C4", "22n", *rep, (68.58, 93.98), rot=90, fields="below")
    r4 = s.part(R, "R4", "2.2k", *rep, (50.8, 104.14), fields="left")
    r5 = s.part(R, "R5", "22k", *rep, (86.36, 104.14), fields="right")
    c5 = s.part(C, "C5", "22n", *rep, (99.06, 71.12), rot=90, fields="above")
    r6 = s.part(R, "R6", "100k", *rep, (111.76, 81.28), fields="right")
    s.wire((38.1, 71.12), (50.8, 71.12), r3["1"])
    s.wire((50.8, 71.12), c2["1"])
    s.wire(r3["2"], (86.36, 71.12), c5["1"])
    s.wire((86.36, 71.12), c3["1"])
    s.wire(c2["2"], (50.8, 93.98), c4["1"])
    s.wire(c3["2"], (86.36, 93.98), c4["2"])
    s.wire((50.8, 93.98), r4["1"])
    s.wire((86.36, 93.98), r5["1"])
    for part in (r4, r5):
        s.wire(part["2"], (part["2"][0], 114.3))
        s.glabel("VB", (part["2"][0], 114.3), 270)
    s.wire(c5["2"], (111.76, 71.12), r6["1"])
    s.wire(r6["2"], (111.76, 91.44))
    s.glabel("VB", (111.76, 91.44), 270)
    s.wire((111.76, 71.12), (129.54, 71.12))
    s.hlabel("OUT", (129.54, 71.12))
    s.text(
        [
            "Nodal analysis (tools/basspreamp-networks.py):",
            "poles 26.9, 117.9 and 400.8 Hz; zeros 0, 160 and 2251 Hz",
            "a broad band-pass: -10.2 dB at 110 Hz, -19.0 dB at 1 kHz",
        ],
        (99.06, 104.14),
    )
    s.note(
        [
            "Section 3 of the circuit notes. R3 bridged by C2-C4-C3 to VB through R4 and R5, then C5 into the Presence",
            "stage with R6 to VB, as traced [2]. Its function, a bass-heavy feed for the clipping stages, is inferred.",
            "The DSP implements its transfer function exactly, assuming an ideal buffer before it and no load after it.",
        ]
    )
    return s


def gain_stage(p, number, title):
    """Sections 4 and 5: non-inverting stages with R || C feedback and a
    rheostat in the ground leg. Presence has a capacitor in that leg."""
    presence = number == 4
    s = p.sheet(number, title, pins=[("IN", "input"), ("OUT", "output")])
    s.heading(f"{number} {title}")
    rep = ("reported", "[2]")
    u = s.part(OPAMP, "IC2_C" if presence else "IC2_D", *TL, (106.68, 76.2), fields="upright")
    s.opamp_power(u)
    s.hlabel("IN", (63.5, 73.66), 180)
    s.wire((63.5, 73.66), u["+"])
    s.wire(u["-"], (93.98, 78.74), (76.2, 78.74))
    if presence:
        leg = [(C, "C7", "10n", *rep), (R, "R8", "3.3k", *rep), (RVAR, "RVX1", "100k lin (Presence)", *rep)]
        cf, rf = ("C6", "220p"), ("R7", "330k")
    else:
        leg = [(R, "R10", "3.3k", *rep), (RVAR, "RVX2", "100k lin (Drive)", *rep)]
        cf, rf = ("C8", "220p"), ("R9", "330k")
    end = series(s, 76.2, 78.74, leg, ground=False)
    s.wire(end, (76.2, end[1] + 3.81))
    s.glabel("VB", (76.2, end[1] + 3.81), 270)
    c = s.part(C, cf[0], cf[1], *rep, (110.49, 96.52), rot=90, fields="below")
    r = s.part(R, rf[0], rf[1], *rep, (110.49, 114.3), rot=90, fields="below")
    left, right = 93.98, 127.0
    s.wire((left, 78.74), (left, 114.3), r["1"])
    s.wire((left, 96.52), c["1"])
    s.wire(c["2"], (right, 96.52))
    s.wire(r["2"], (right, 114.3), (right, 76.2))
    s.wire(u["5"], (right, 76.2), (139.7, 76.2))
    s.hlabel("OUT", (139.7, 76.2))

    f_hi = expect("feedback roll-off", rc_hz(rf[1], cf[1]), 2190, rel=0.01)
    if presence:
        f_lo = expect("R7, C7 rise", rc_hz("330k", "10n"), 48, rel=0.01)
        f_r8 = expect("R8, C7 corner", rc_hz("3.3k", "10n"), 4800, rel=0.01)
        lines = [
            f"R7 with C7: rise from {hz(f_lo)}",
            f"R7 with C6: roll-off above {hz(f_hi)}",
            f"R8 with C7: {hz(f_r8)} (full Presence)",
            "boost about +12 dB (min) to +30 dB (max)",
        ]
        note = [
            "Section 4 of the circuit notes. IC2_C: H = 1 + Zf/Zg, Zf = R7 || C6, Zg = C7 + R8 + the Presence pot, as traced [2]:",
            "unity at DC and a boost-only rise in the upper mids. RVX1: the traced 100 kOhm linear pot as a rheostat;",
            "the DSP sweeps it log-uniformly from 103.3 kOhm to 3.3 kOhm instead (chosen, section 4).",
        ]
    else:
        g0 = expect("Drive gain at minimum", 1 + val("330k") / (val("3.3k") + val("100k")), 4.2, rel=0.01)
        g1 = expect("Drive gain at maximum", 1 + val("330k") / val("3.3k"), 101, rel=0.01)
        lines = [f"G = 1 + R9/(R10 + pot): {g0:.1f} to {g1:.0f}", f"extra gain rolls off above {hz(f_hi)}"]
        note = [
            "Section 5 of the circuit notes. IC2_D: H = 1 + (G - 1)/(1 + s R9 C8), with no capacitor in the ground leg, as traced [2].",
            "RVX2: the traced 100 kOhm linear pot as a rheostat; the DSP makes G log-uniform in the control (chosen).",
        ]
    s.text(lines, (132.08, 101.6))
    s.note(
        note
        + [
            "Section 6: there are no clipping diodes [2]. The op-amp clips at its rails, about +/-3.1 V around VB (railV, inferred",
            "from the TL07x datasheet [4]); the DSP's knee and its 2 mV input offset (vos) are chosen.",
        ]
    )
    return s


def voicing(p):
    s = p.sheet(7, "Speaker voicing", pins=[("IN", "input"), ("OUT", "output")])
    s.heading('7 The fixed "speaker" voicing')
    rep = ("reported", "[2]")
    y = 76.2
    s.hlabel("IN", (22.86, y), 180)

    def down(part_spec, x, top, vb_y):
        part = s.part(*part_spec[:5], (x, top + 7.62), fields="left")
        s.wire((x, top), part["1"])
        s.wire(part["2"], (x, vb_y))
        s.glabel("VB", (x, vb_y), 270)
        return part

    # 1. Divider and first Sallen-Key low-pass with the R14 + C10 shelf leg.
    r11 = s.part(R, "R11", "10k", *rep, (33.02, y), rot=90, fields="above")
    s.wire((22.86, y), r11["1"])
    s.wire(r11["2"], (43.18, y))
    down((R, "R12", "22k", *rep), 43.18, y, 93.98)
    r13 = s.part(R, "R13", "22k", *rep, (55.88, y), rot=90, fields="above")
    s.wire((43.18, y), r13["1"])
    s.wire(r13["2"], (68.58, y))
    r14 = s.part(R, "R14", "10k", *rep, (68.58, 83.82), fields="left")
    c10 = s.part(C, "C10", "47n", *rep, (68.58, 95.25), fields="left")
    s.wire((68.58, y), r14["1"])
    s.wire(r14["2"], c10["1"])
    s.wire(c10["2"], (68.58, 104.14))
    s.glabel("VB", (68.58, 104.14), 270)
    r15 = s.part(R, "R15", "22k", *rep, (81.28, y), rot=90, fields="above")
    s.wire((68.58, y), r15["1"])
    u1 = s.part(OPAMP, "IC2_A", *TL, (111.76, 78.74), fields="upright")
    s.opamp_power(u1)
    s.wire(r15["2"], (96.52, y), u1["+"])
    down((C, "C11", "470p", *rep), 96.52, y, 91.44)
    c9 = s.part(C, "C9", "10n", *rep, (88.9, 60.96), rot=90, fields="above")
    o1 = (129.54, 78.74)
    s.wire((68.58, y), (68.58, 60.96), c9["1"])
    s.wire(c9["2"], (o1[0], 60.96), o1)
    s.wire(u1["-"], (104.14, 96.52), (o1[0], 96.52), o1)
    s.wire(u1["5"], o1)

    # 2. Second Sallen-Key low-pass.
    r16 = s.part(R, "R16", "33k", *rep, (139.7, 78.74), rot=90, fields="above")
    r17 = s.part(R, "R17", "33k", *rep, (157.48, 78.74), rot=90, fields="above")
    u2 = s.part(OPAMP, "IC2_B", *TL, (177.8, 81.28), fields="upright")
    s.opamp_power(u2)
    s.wire(o1, r16["1"])
    s.wire(r16["2"], (149.86, 78.74), r17["1"])
    s.wire(r17["2"], (165.1, 78.74), u2["+"])
    down((C, "C13", "1.2n", *rep), 165.1, 78.74, 96.52)
    o2 = (185.42, 81.28)
    c12 = s.part(C, "C12", "2.2n", *rep, (167.64, 63.5), rot=90, fields="above")
    s.wire((149.86, 78.74), (149.86, 63.5), c12["1"])
    s.wire(c12["2"], (o2[0], 63.5), o2)
    s.wire(u2["-"], (170.18, 99.06), (o2[0], 99.06), o2)
    s.wire(u2["5"], o2)

    # 3. Bridged-T notch into the buffer IC1_A.
    r18 = s.part(R, "R18", "22k", *rep, (200.66, 81.28), rot=90, fields="above")
    c14 = s.part(C, "C14", "22n", *rep, (200.66, 93.98), rot=90, fields="below")
    c15 = s.part(C, "C15", "47n", *rep, (210.82, 87.63), fields="right")
    r19 = s.part(R, "R19", "6.2k", *rep, (210.82, 101.6), fields="right")
    u3 = s.part(OPAMP, "IC1_A", *TL, (236.22, 83.82), fields="upright")
    s.opamp_power(u3)
    s.wire(o2, r18["1"])
    s.wire(r18["2"], (210.82, 81.28), u3["+"])
    s.wire((190.5, 81.28), (190.5, 93.98), c14["1"])
    s.wire(c14["2"], (210.82, 93.98))
    s.wire((210.82, 81.28), c15["1"])
    s.wire(c15["2"], (210.82, 93.98), r19["1"])
    s.wire(r19["2"], (210.82, 111.76))
    s.glabel("VB", (210.82, 111.76), 270)
    o3 = (248.92, 83.82)
    s.wire(u3["-"], (228.6, 104.14), (o3[0], 104.14), o3)
    s.wire(u3["5"], o3, (259.08, 83.82))
    s.hlabel("OUT", (259.08, 83.82))

    f2 = expect("second Sallen-Key", 1 / (2 * math.pi * val("33k") * math.sqrt(val("2.2n") * val("1.2n"))), 2970, rel=0.01)
    q2 = expect("second Sallen-Key Q", 0.5 * math.sqrt(val("2.2n") / val("1.2n")), 0.68, rel=0.01)
    s.text(["1: pole 86.7 Hz, zero 338.6 Hz,", "resonant pair 5.76 kHz, Q 1.85"], (38.1, 121.92))
    s.text([f"2: {hz(f2)}, Q {q2:.2f}"], (139.7, 121.92))
    s.text(["3: notch about -11 dB", "at 424 Hz"], (200.66, 124.46))
    s.note(
        [
            "Section 7 of the circuit notes, as traced [2]: R11/R12 divider, Sallen-Key low-pass IC2_A with the R14 + C10 shelf leg,",
            "Sallen-Key low-pass IC2_B, and the R18/C14/C15/R19 bridged-T notch into the buffer IC1_A. All values reported;",
            "their role as a speaker simulation is inferred. Poles, zeros and the notch come from tools/basspreamp-networks.py,",
            "which also writes the DSP's coefficients, with ideal op-amps.",
        ]
    )
    return s


def blend(p):
    s = p.sheet(8, "Blend and level", pins=[("DRIVEN", "input"), ("CLEAN", "input"), ("OUT", "output")])
    s.heading("8 Blend, level and calibration")
    rep = ("reported", "[2]")
    s.hlabel("DRIVEN", (40.64, 63.5), 180)
    s.hlabel("CLEAN", (40.64, 93.98), 180)
    c16 = s.part(C, "C16", "47n", *rep, (55.88, 63.5), rot=90, fields="above")
    pot = s.part(POT, "RVX3", "100k lin (Blend)", *rep, (88.9, 78.74), fields="left")
    s.wire((40.64, 63.5), c16["1"])
    s.wire(c16["2"], (88.9, 63.5), pot["1"])
    s.wire((40.64, 93.98), (88.9, 93.98), pot["3"])
    u = s.part(OPAMP, "IC1_C", *TL, (110.49, 81.28), fields="upright")
    s.opamp_power(u)
    s.wire(pot["2"], u["+"])
    o1 = (124.46, 81.28)
    s.wire(u["-"], (102.87, 99.06), (o1[0], 99.06), o1)
    s.wire(u["5"], o1)
    # Mixer IC1_B, x2.2.
    u2 = s.part(OPAMP, "IC1_B", *TL, (149.86, 83.82), fields="upright")
    s.opamp_power(u2)
    s.wire(o1, (142.24, 81.28))
    rg = s.part(R, "RX3", "10k", "chosen", "-", (142.24, 104.14), fields="left")
    rf = s.part(R, "RX4", "12k", "chosen", "-", (154.94, 96.52), rot=90, fields="below")
    s.wire(u2["-"], (142.24, 96.52), rg["1"])
    s.wire(rg["2"], (142.24, 114.3))
    s.glabel("VB", (142.24, 114.3), 270)
    s.wire((142.24, 96.52), rf["1"])
    o2 = (165.1, 83.82)
    s.wire(rf["2"], (o2[0], 96.52), o2)
    s.wire(u2["5"], o2)
    lvl = s.part(POT, "RVX4", "100k log (Level)", "chosen", "-", (175.26, 91.44), fields="upright")
    s.wire(o2, (175.26, 83.82), lvl["1"])
    s.wire(lvl["3"], (175.26, 101.6))
    s.glabel("VB", (175.26, 101.6), 270)
    s.wire(lvl["2"], (203.2, 91.44))
    s.hlabel("OUT", (203.2, 91.44))

    f = expect("C16 into the Blend pot (fcBlend)", rc_hz("100k", "47n"), 34, rel=0.01)
    g = expect("mixer gain", 1 + val("12k") / val("10k"), 2.2, rel=0.01)
    s.text([f"C16 with the pot: {hz(f)}", "lows below it pass clean at every Blend"], (43.18, 109.22))
    s.text(f"x{g:.1f}", (154.94, 111.76))
    s.note(
        [
            "Section 8 of the circuit notes. C16 and the 100 kOhm linear Blend pot, its other end tied to the input buffer, as",
            "traced [2]; the follower IC1_C gives clean + b HP(driven - clean), modelled exactly. IC1_B: the mixer's x2.2 gain",
            "is traced [2]; RX3 and RX4 are chosen to give it. RVX4: the Level pot, value chosen. The DSP replaces the mixer",
            "gain and Level with a Level control in dB, and trims the driven path (drvTrim = 0.32, chosen).",
        ]
    )
    return s


def chain(s, x, y, parts):
    """A vertical chain from (x, y) to ground. Each entry is (lib, ref, value)
    or (lib, ref, value, switch_ref, switch_value): the switch, drawn to the
    right, shorts that part when closed."""
    prev = (x, y)
    for i, (lib, ref, value, *sw) in enumerate(parts):
        cy = y + 10.16 + i * 11.43
        part = s.part(lib, ref, value, "chosen", "-", (x, cy), fields="left")
        s.wire(prev, part["1"])
        prev = part["2"]
        if sw:
            sx = x + 7.62
            sw_part = s.part(SW, sw[0], sw[1], "chosen", "-", (sx, cy), rot=90, fields="right")
            top, bot = (x, cy - 5.08), (x, cy + 5.08)
            s.wire(top, sw_part["2"])
            s.wire(bot, sw_part["1"])
    gnd = (x, prev[1] + 5.08)
    s.wire(prev, gnd)
    s.gnd(gnd)


def eq(p):
    s = p.sheet(9, "EQ", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("9 The V2 EQ (chosen stand-in)")
    y = 50.8
    x0 = 27.94
    s.hlabel("IN", (20.32, y), 180)

    # Bass: low shelf, half its range at 80 Hz, or 40 Hz with Bass Shift (switch open).
    bin_, bout, bw = band(s, x0, y, ("RX5", "RVX5", "RX6", "UX1"), ("3k", "100k (Bass)", "3k", "OPAMP"))
    s.wire((20.32, y), bin_)
    chain(s, bw[0], bw[1], [(R, "RX7", "1k"), (L, "LX1", "3.98H"), (L, "LX2", "3.98H", "SWX1", "Bass Shift")])
    f80 = expect("bass shelf midpoint", math.sqrt(val("1k") * (val("1k") + val("3k"))) / (2 * math.pi * 3.98), 80, rel=0.01)
    f40 = expect("bass shelf with Bass Shift", f80 / 2, 40, rel=0.01)
    g_b = expect("bass range", 20 * math.log10((val("3k") + val("1k")) / val("1k")), 12, rel=0.01)
    s.text([f"Bass: shelf, half at {hz(f80)}", f"({hz(f40)} with Bass Shift), +/-{g_b:.0f} dB"], (x0 + 25.4, y + 73.66))

    # Mid: peaking band at 500 Hz, Q 0.7, or 1 kHz with Mid Shift (SWX2 closed, SWX3 open).
    x1 = x0 + 66.04
    min_, mout, mw = band(s, x1, y, ("RX8", "RVX6", "RX9", "UX2"), ("3k", "100k (Mid)", "3k", "OPAMP"))
    s.wire(bout, (x1 + 1.27, bout[1]), (x1 + 1.27, y), min_)
    chain(
        s,
        mw[0],
        mw[1],
        [
            (R, "RX10", "1k"),
            (L, "LX3", "0.23H"),
            (L, "LX4", "0.23H", "SWX2", "Mid Shift"),
            (C, "CX2", "220n"),
            (C, "CX3", "220n", "SWX3", "Mid Shift"),
        ],
    )
    f500 = expect("mid centre", lc_hz(2 * val("0.23"), "220n"), 500, rel=0.02)
    f1k = expect("mid centre with Mid Shift", lc_hz("0.23", val("220n") / 2), 1000, rel=0.02)
    q = expect("mid Q", 2 * math.pi * f500 * 0.46 / (2 * val("1k")), 0.7, rel=0.05)
    s.text([f"Mid: {hz(f500)} ({hz(f1k)} with Mid Shift)", f"Q {q:.2f}, +/-12 dB"], (x1 + 15.24, y + 96.52))

    # Treble: high shelf, half its range at 2.8 kHz.
    x2 = x1 + 66.04
    tin, tout, tw = band(s, x2, y, ("RX11", "RVX7", "RX12", "UX3"), ("7.5k", "100k (Treble)", "7.5k", "OPAMP"))
    s.wire(mout, (x2 + 1.27, mout[1]), (x2 + 1.27, y), tin)
    series(s, tw[0], tw[1], [(R, "RX13", "2.4k"), (C, "CX4", "12n")])
    g_t = expect("treble range", 20 * math.log10((val("7.5k") + val("2.4k")) / val("2.4k")), 12, rel=0.03)
    f_t = expect(
        "treble shelf midpoint",
        math.sqrt(rc_hz("2.4k", "12n") * rc_hz(val("7.5k") + val("2.4k"), "12n")),
        2800,
        rel=0.03,
    )
    s.text([f"Treble: half at {hz(f_t)}", f"+/-{g_t:.1f} dB"], (x2 + 25.4, y + 50.8))
    s.wire(tout, (x2 + 60.96, tout[1]))
    s.hlabel("OUT", (x2 + 60.96, tout[1]))

    s.note(
        [
            "Section 9 of the circuit notes. The later version's EQ schematic is not public; the DSP builds it from the published",
            "specification [1], [3] with digital filters, and this sheet is an analogue stand-in for them, all chosen. Each band is a",
            "graphic-EQ boost/cut stage: flat with its pot centred, +/-12 dB at the ends. LX1-LX4 are simulated inductors (gyrators).",
            "Bass: low shelf at 80 Hz; Bass Shift opens SWX1, doubling the inductance for 40 Hz. Mid: 500 Hz, Q 0.7; Mid Shift is",
            "one two-pole switch, SWX2 (closes, halving the inductance) and SWX3 (opens, halving the capacitance), for 1 kHz at the",
            "same Q. Treble: high shelf at 2.8 kHz (inferred in the notes from the earlier version's tone stack).",
            "The DSP's shelves are third-order and its mid band constant-Q, so the slopes here are gentler.",
        ]
    )
    return s
