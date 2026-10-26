# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""BassDrive's modelled circuit, for tools/schematics/build.py.

No public schematic of the reference pedal was found, so this is the circuit
src/bassdrive.dsp implements, redrawn as analogue stages, not a trace of the
pedal. Sheets are numbered and named after the sections of
docs/bassdrive/circuit-notes.md; sources [n] are that file's source list.
Every value is checked against the notes or the DSP constant it stands for
with expect(), so the drawing can't drift from them.
"""

import math

import stages
from kicadsch import Project, expect, hz, lc_hz, rc_hz, val
from stages import CP, JACK, LED, OPAMP, POT, RVAR, C, D, L, R, band, series

CAVEAT = "Modelled circuit (src/bassdrive.dsp), not a trace of the pedal"


def project():
    p = Project(
        "bassdrive",
        "BassDrive",
        hardware="Boss ODB-3",
        date="2026-10-26",
        caveat=CAVEAT,
    )
    sheets = [
        supply(p),
        input_buffer(p),
        pre_emphasis(p),
        clipping(p),
        post_filter(p),
        eq(p),
        balance(p),
        level(p),
    ]
    root(p, *sheets)
    return p


# ---------------------------------------------------------------------------


def root(p, sup, buf, emph, clip, post, eq_, bal, lvl):
    s = p.root
    s.heading("BassDrive: modelled circuit")
    s.text(
        [
            "Block diagram of section 2 of docs/bassdrive/circuit-notes.md: one sub-sheet per modelled stage,",
            "numbered and named after the section that describes it. No public schematic of the reference pedal",
            "was found, so this is the circuit src/bassdrive.dsp implements, not a trace of the pedal.",
        ],
        (25.4, 43.18),
    )
    p.block(sup, (40.64, 134.62), (38.1, 15.24))

    y1, y2 = 60.96, 106.68
    b2 = p.block(buf, (40.64, y1))
    b3 = p.block(emph, (91.44, y1))
    b5 = p.block(clip, (142.24, y1))
    b6 = p.block(post, (193.04, y1))
    b8 = p.block(bal, (40.64, y2))
    b7 = p.block(eq_, (91.44, y2))
    b9 = p.block(lvl, (142.24, y2))

    # Input and output jacks: the pedal's documented interface [1].
    j1 = s.part(
        JACK, "JX1", "Input", "documented", "[1]", (25.4, 66.04), fields="above", mirror="x"
    )
    s.wire(j1["T"], b2["IN"])
    s.wire(j1["S"], (33.02, j1["S"][1]), (33.02, 73.66))
    s.gnd((33.02, 73.66))

    s.wire(b2["OUT"], b3["IN"])
    s.wire(b3["OUT"], b5["IN"])
    s.wire(b5["OUT"], b6["IN"])

    # Clean path from the buffer, driven path from the post-filter, into the blend.
    jx = b2["OUT"][0] + 6.35
    s.wire((jx, b2["OUT"][1]), (jx, 91.44), (33.02, 91.44), (33.02, b8["CLEAN"][1]), b8["CLEAN"])
    s.wire(b6["OUT"], (b6["OUT"][0] + 5.08, b6["OUT"][1]), (b6["OUT"][0] + 5.08, 96.52))
    s.wire((b6["OUT"][0] + 5.08, 96.52), (35.56, 96.52), (35.56, b8["DRIVEN"][1]), b8["DRIVEN"])

    s.wire(b8["OUT"], b7["IN"])
    s.wire(b7["OUT"], b9["IN"])
    j2 = s.part(
        JACK, "JX2", "Output", "documented", "[1]", (205.74, 111.76), rot=180, fields="above"
    )
    s.wire(b9["OUT"], j2["T"])
    s.wire(j2["S"], (198.12, j2["S"][1]), (198.12, 119.38))
    s.gnd((198.12, 119.38))

    s.text("clean", (jx + 1.27, 90.17))
    s.text("driven", (200.66, 95.25))
    s.text(
        [
            "In the DSP the clean path is delayed by 32 samples to line up with the",
            "4x oversampler; that delay has no circuit counterpart (section 8).",
        ],
        (91.44, 147.32),
    )


def supply(p):
    return stages.supply(
        p,
        [
            "Section 1 of the circuit notes: the pedal runs on a 9 V supply (documented [1]).",
            "RX1, RX2, CX1: a half-supply bias rail VB for the single-supply op-amps (chosen; the usual arrangement,",
            "not described by any source). Every other sheet takes +9V, GND and VB from here.",
        ],
    )


def input_buffer(p):
    s = p.sheet(2, "Input buffer", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("2 Input buffer")
    s.hlabel("IN", (38.1, 76.2), 180)
    c = s.part(C, "CX2", "33n", "chosen", "-", (48.26, 76.2), rot=90, fields="above")
    r = s.part(R, "RX3", "1M", "inferred", "[1]", (66.04, 83.82), fields="left")
    u = s.part(OPAMP, "UX1", "RC4558", "inferred", "[5]", (88.9, 78.74), fields="upright")
    s.wire((38.1, 76.2), c["1"])
    s.wire(c["2"], (66.04, 76.2), u["+"])
    s.wire((66.04, 76.2), r["1"])
    s.wire(r["2"], (66.04, 91.44))
    s.glabel("VB", (66.04, 91.44), 270)
    s.opamp_power(u)
    s.wire(u["-"], (81.28, 96.52), (109.22, 96.52), (109.22, 78.74))
    s.wire(u["5"], (121.92, 78.74))
    s.hlabel("OUT", (121.92, 78.74))
    f = expect("input high-pass", rc_hz("1M", "33n"), 5.0)
    s.text(f"CX2 with RX3: {hz(f)}", (45.72, 104.14))
    s.text("(DSP: 5 Hz DC blocker)", (45.72, 106.68))
    s.note(
        [
            "Section 2 of the circuit notes. The output feeds both the clean path and the driven path.",
            "RX3: the documented 1 MOhm input impedance [1], as a bias resistor to VB (position inferred).",
            "CX2: input coupling, chosen with RX3 for the DSP's 5 Hz DC blocker (fi.dcblockerat(5)).",
            "UX1: a unity-gain buffer. The pedal has RC4558 op-amps [5]; that one buffers the input is inferred.",
        ]
    )
    return s


def pre_emphasis(p):
    s = p.sheet(3, "Pre-emphasis", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("3 Pre-emphasis (stage 1) and 4 Feedback low-pass")
    u = s.part(OPAMP, "UX2", "OPAMP", "chosen", "[4]", (106.68, 76.2), fields="upright")
    s.opamp_power(u)
    s.hlabel("IN", (63.5, 73.66), 180)
    s.wire((63.5, 73.66), u["+"])
    # Ground leg: R31 in series with C10 (section 3).
    r31 = s.part(R, "R31", "3.3k", "inferred", "[2]", (76.2, 86.36), fields="left")
    c10 = s.part(C, "C10", "33n", "inferred", "[2]", (76.2, 97.79))
    s.wire(u["-"], (93.98, 78.74), (76.2, 78.74), r31["1"])
    s.wire(r31["2"], c10["1"])
    s.gnd((76.2, 104.14))
    s.wire(c10["2"], (76.2, 104.14))
    # Feedback: C8 across the Gain pot and its series resistor (section 4).
    c8 = s.part(C, "C8", "300p", "inferred", "[2]", (106.68, 99.06), rot=90, fields="below")
    rv = s.part(
        RVAR, "RVX1", "1M log (Gain)", "chosen", "-", (101.6, 132.08), rot=90, fields="above"
    )
    rx = s.part(R, "RX4", "3.3k", "chosen", "-", (116.84, 132.08), rot=90, fields="above")
    s.wire((93.98, 78.74), (93.98, 99.06), c8["1"])
    s.wire((93.98, 99.06), (93.98, 132.08), rv["1"])
    s.wire(rv["2"], rx["1"])
    s.wire(rx["2"], (127, 132.08), (127, 99.06), c8["2"])
    s.wire((127, 99.06), (127, 76.2))
    s.wire(u["5"], (127, 76.2), (139.7, 76.2))
    s.hlabel("OUT", (139.7, 76.2))

    f_emph = expect("R31, C10 corner", rc_hz("3.3k", "33n"), 1460)
    rf_max = val("1M") + val("3.3k")
    expect("Rf/R31 at maximum Gain", rf_max / val("3.3k"), 304, rel=0.01)
    f_fb = expect("C8 corner at maximum Gain", rc_hz(rf_max, "300p"), 530, rel=0.02)
    s.text([f"R31 with C10: {hz(f_emph)}", "gain rises above it"], (38.1, 111.76))
    s.text(
        [f"C8 with Rf: {hz(f_fb)} at maximum Gain", "Rf/R31 = 1 (min), ~30 (noon), 304 (max)"],
        (139.7, 104.14),
    )
    s.text("Rf = RVX1 + RX4", (99.06, 144.78))
    s.note(
        [
            "Sections 3 and 4 of the circuit notes. G = 1 + (Rf/R31) HP(1.46 kHz) LP(Rf, C8): bass passes near unity, the upper register is driven.",
            "R31, C10, C8: values reported by a mod [2]; their position in a non-inverting stage is inferred (the standard topology).",
            "UX2: the core is reported as a discrete two-stage circuit [4]; an ideal op-amp stands in for its small-signal behaviour (chosen).",
            "RVX1, RX4: Gain pot and series resistor (chosen, section 4): 1 MOhm log, about 10 % of its value at noon.",
            "Stage 1 headroom: the DSP soft-limits at +/-4 V around VB on the 9 V supply (railV, chosen, section 5).",
        ]
    )
    return s


def clipping(p):
    s = p.sheet(5, "Clipping", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("5 Clipping (stage 2)")
    u = s.part(OPAMP, "UX3", "OPAMP", "chosen", "[4]", (76.2, 76.2), fields="upright")
    s.opamp_power(u)
    s.hlabel("IN", (50.8, 73.66), 180)
    s.wire((50.8, 73.66), u["+"])
    rg = s.part(R, "RX5", "1k", "chosen", "-", (58.42, 86.36), fields="left")
    rf = s.part(R, "RX6", "2k", "chosen", "-", (76.2, 101.6), rot=90, fields="below")
    s.wire(u["-"], (63.5, 78.74), (58.42, 78.74), rg["1"])
    s.wire(rg["2"], (58.42, 93.98))
    s.glabel("VB", (58.42, 93.98), 270)
    s.wire((63.5, 78.74), (63.5, 101.6), rf["1"])
    s.wire(rf["2"], (91.44, 101.6), (91.44, 76.2))
    s.wire(u["5"], (91.44, 76.2))
    rs = s.part(R, "RX7", "1k", "chosen", "-", (99.06, 76.2), rot=90, fields="above")
    s.wire((91.44, 76.2), rs["1"])
    # LEDs D2 and D3 in anti-parallel to VB [2]; DX1 clips the negative side first.
    d2 = s.part(
        LED, "D2", "red LED", "inferred", "[2], [4]", (111.76, 86.36), rot=90, fields="left"
    )
    d3 = s.part(LED, "D3", "red LED", "inferred", "[2], [4]", (129.54, 86.36), rot=270)
    dx = s.part(D, "DX1", "1N4148", "chosen", "-", (154.94, 86.36), rot=270)
    s.wire(rs["2"], (111.76, 76.2), d2["A"])
    s.wire((111.76, 76.2), (129.54, 76.2), d3["K"])
    s.wire((129.54, 76.2), (154.94, 76.2), dx["K"])
    s.wire(d2["K"], (111.76, 96.52), (129.54, 96.52), d3["A"])
    s.wire((129.54, 96.52), (154.94, 96.52), dx["A"])
    s.wire((111.76, 96.52), (111.76, 101.6))
    s.glabel("VB", (111.76, 101.6), 270)
    s.wire((154.94, 76.2), (172.72, 76.2))
    s.hlabel("OUT", (172.72, 76.2))

    g = expect("stage 2 gain", 1 + val("2k") / val("1k"), 3.0)
    s.text(f"gain {g:g} (stage2G)", (66.04, 116.84))
    s.text(["+1.7 V (LED, ledPos)", "-1.7 V (LED)"], (114.3, 111.76))
    s.text(["about -0.6 to -0.8 V", "(ledNeg = 0.8 V)"], (157.48, 111.76))
    s.note(
        [
            "Section 5 of the circuit notes. LED clipping in the second stage is reported [4]; the LEDs D2 and D3 in anti-parallel,",
            "red, about 1.5-1.8 V, are reported by a mod [2]. Their place as a shunt to VB after the gain stage is inferred.",
            "UX3, RX5, RX6: stage 2 as an ideal op-amp with a fixed gain of 3 (stage2G, chosen and tuned by measurement).",
            "RX7: series resistor feeding the clippers (chosen). DX1: a one-sided silicon clip standing in for the off-centre biased",
            "discrete stage the notes infer for the even harmonics. The DSP's knee is x/(1+|x/0.8|^6)^(1/6) (ledNeg, negKnee, chosen).",
        ]
    )
    return s


def post_filter(p):
    s = p.sheet(6, "Post-filtering", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("6 Post-filtering")
    s.hlabel("IN", (40.64, 76.2), 180)
    c1 = s.part(C, "CX3", "1u", "chosen", "-", (53.34, 76.2), rot=90, fields="above")
    r1 = s.part(R, "RX8", "33k", "chosen", "-", (63.5, 83.82), fields="left")
    s.wire((40.64, 76.2), c1["1"])
    s.wire(c1["2"], (63.5, 76.2), r1["1"])
    s.wire(r1["2"], (63.5, 91.44))
    s.glabel("VB", (63.5, 91.44), 270)
    # Unity-gain Sallen-Key low-pass.
    ra = s.part(R, "RX9", "10k", "chosen", "-", (73.66, 76.2), rot=90, fields="below")
    rb = s.part(R, "RX10", "10k", "chosen", "-", (93.98, 76.2), rot=90, fields="above")
    u = s.part(OPAMP, "UX4", "OPAMP", "chosen", "-", (116.84, 78.74), fields="upright")
    s.opamp_power(u)
    cg = s.part(C, "CX4", "2.2n", "chosen", "-", (101.6, 83.82), fields="left")
    cf = s.part(C, "CX5", "4.7n", "chosen", "-", (104.14, 53.34), rot=90, fields="above")
    s.wire((63.5, 76.2), ra["1"])
    s.wire(ra["2"], (83.82, 76.2), rb["1"])
    s.wire(rb["2"], (101.6, 76.2), u["+"])
    s.wire((101.6, 76.2), cg["1"])
    s.gnd((101.6, 91.44))
    s.wire(cg["2"], (101.6, 91.44))
    s.wire((83.82, 76.2), (83.82, 53.34), cf["1"])
    s.wire(cf["2"], (134.62, 53.34), (134.62, 78.74))
    s.wire(u["-"], (109.22, 96.52), (134.62, 96.52), (134.62, 78.74))
    s.wire(u["5"], (134.62, 78.74), (149.86, 78.74))
    s.hlabel("OUT", (149.86, 78.74))

    f_dc = expect("post DC blocker", rc_hz("33k", "1u"), 5.0)
    f_lp = expect(
        "post low-pass", 1 / (2 * math.pi * val("10k") * math.sqrt(val("4.7n") * val("2.2n"))), 5000
    )
    q = expect("post low-pass Q", 0.5 * math.sqrt(val("4.7n") / val("2.2n")), 1 / math.sqrt(2))
    s.text(f"CX3 with RX8: {hz(f_dc)}", (40.64, 101.6))
    s.text(
        [f"Sallen-Key: {hz(f_lp)}, Q {q:.2f}", "(DSP: 2nd-order 5 kHz low-pass)"], (139.7, 66.04)
    )
    s.note(
        [
            "Section 6 of the circuit notes. The pedal's post-clip filtering is not documented; everything here is chosen.",
            "CX3, RX8: the 5 Hz DC blocker that removes the asymmetric clipper's offset (fi.dcblockerat(5)).",
            "RX9, RX10, CX4, CX5, UX4: a unity-gain Sallen-Key Butterworth low-pass at 5 kHz (postLP), which tames the fizz",
            "while leaving the Treble control something to act on.",
        ]
    )
    return s


def balance(p):
    s = p.sheet(8, "Balance", pins=[("DRIVEN", "input"), ("CLEAN", "input"), ("OUT", "output")])
    s.heading("8 Balance")
    s.hlabel("CLEAN", (40.64, 63.5), 180)
    s.hlabel("DRIVEN", (40.64, 93.98), 180)
    ra = s.part(R, "RX11", "13k", "chosen", "-", (53.34, 93.98), rot=90, fields="below")
    rb = s.part(R, "RX12", "5.1k", "chosen", "-", (63.5, 104.14), fields="right")
    s.wire((40.64, 93.98), ra["1"])
    s.wire(ra["2"], (63.5, 93.98), rb["1"])
    s.wire(rb["2"], (63.5, 111.76))
    s.glabel("VB", (63.5, 111.76), 270)
    pot = s.part(POT, "RVX2", "100k lin (Balance)", "chosen", "-", (88.9, 78.74), fields="left")
    s.wire((40.64, 63.5), (88.9, 63.5), pot["1"])
    s.wire((63.5, 93.98), (88.9, 93.98), pot["3"])
    u = s.part(OPAMP, "UX5", "OPAMP", "chosen", "-", (110.49, 81.28), fields="upright")
    s.opamp_power(u)
    s.wire(pot["2"], u["+"])
    s.wire(u["-"], (102.87, 101.6), (124.46, 101.6), (124.46, 81.28))
    s.wire(u["5"], (124.46, 81.28), (137.16, 81.28))
    s.hlabel("OUT", (137.16, 81.28))

    trim = expect("driven-path trim", val("5.1k") / (val("13k") + val("5.1k")), 0.28)
    s.text(f"x{trim:.2f} (drvTrim)", (45.72, 116.84))
    s.text(
        ["wiper = clean + b (driven - clean)", "b = 0 clean only, 1 driven only"], (129.54, 68.58)
    )
    s.note(
        [
            "Section 8 of the circuit notes. A clean/driven blend is documented [1]; its circuit is not.",
            "RVX2, UX5: a linear crossfade (chosen). A pot between two low-impedance sources into a follower gives exactly",
            "clean + b (driven - clean), the DSP's blend. RX11, RX12: the driven-path trim drvTrim = 0.28 (chosen, matched by",
            "measurement); their 3.7 kOhm source impedance bends the pot's law by a few per cent.",
        ]
    )
    return s


def eq(p):
    s = p.sheet(7, "EQ and mid scoop", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("7 EQ and the fixed mid scoop")
    y = 60.96
    x0 = 27.94
    s.hlabel("IN", (20.32, y), 180)

    # Bass: peaking band at 110 Hz, Q 0.9, +/-12 dB.
    bin_, bout, bw = band(
        s, x0, y, ("RX13", "RVX3", "RX14", "UX6"), ("3k", "100k (Bass)", "3k", "OPAMP")
    )
    s.wire((20.32, y), bin_)
    series(s, bw[0], bw[1], [(R, "RX15", "1k"), (L, "LX1", "2.55H"), (C, "CX6", "820n")])
    f_b = expect("bass band centre", lc_hz("2.55", "820n"), 110, rel=0.02)
    g_b = expect(
        "bass band range", 20 * math.log10((val("3k") + val("1k")) / val("1k")), 12, rel=0.02
    )
    w0 = 2 * math.pi * f_b
    q_b = expect("bass band Q", math.sqrt((w0 * 2.55 / 1e3) * (w0 * 2.55 / 4e3)), 0.9, rel=0.03)
    s.text([f"Bass: {hz(f_b)}, Q {q_b:.2f}", f"+/-{g_b:.0f} dB"], (x0 + 25.4, y + 50.8))

    # Fixed mid scoop: -6 dB at 350 Hz, Q 0.7, then a follower.
    x1 = x0 + 55.88
    r1 = s.part(R, "RX16", "4.7k", "chosen", "-", (x1 + 7.62, y), rot=90, fields="above")
    s.wire(bout, (x1 + 1.27, bout[1]), (x1 + 1.27, y), r1["1"])
    u7 = s.part(OPAMP, "UX7", "OPAMP", "chosen", "-", (x1 + 33.02, y + 2.54), fields="upright")
    s.opamp_power(u7)
    s.wire(r1["2"], (x1 + 15.24, y), u7["+"])
    series(s, x1 + 15.24, y, [(R, "RX17", "4.7k"), (L, "LX2", "2.07H"), (C, "CX7", "100n")])
    sout = (x1 + 50.8, y + 2.54)
    s.wire(u7["-"], (x1 + 25.4, y + 20.32), (sout[0], y + 20.32), sout)
    s.wire(u7["5"], sout)
    f_s = expect("scoop centre", lc_hz("2.07", "100n"), 350, rel=0.02)
    depth = expect(
        "scoop depth", 20 * math.log10(val("4.7k") / (val("4.7k") + val("4.7k"))), -6, rel=0.02
    )
    w0 = 2 * math.pi * f_s
    q_s = expect("scoop Q", math.sqrt((w0 * 2.07 / 4.7e3) * (w0 * 2.07 / 9.4e3)), 0.7, rel=0.03)
    s.text([f"Scoop: {hz(f_s)}, Q {q_s:.2f}", f"{depth:.0f} dB (scoopDB)"], (x1 + 22.86, y + 33.02))

    # Treble: shelf, half its range at 2.5 kHz, +/-15 dB.
    x2 = x1 + 55.88
    tin, tout, tw = band(
        s, x2, y, ("RX18", "RVX4", "RX19", "UX8"), ("12k", "100k (Treble)", "12k", "OPAMP")
    )
    s.wire(sout, (x2 + 1.27, sout[1]), (x2 + 1.27, y), tin)
    series(s, tw[0], tw[1], [(R, "RX20", "2.7k"), (C, "CX8", "10n")])
    g_t = expect(
        "treble range", 20 * math.log10((val("12k") + val("2.7k")) / val("2.7k")), 15, rel=0.03
    )
    f_mid = expect(
        "treble shelf midpoint",
        math.sqrt(rc_hz("2.7k", "10n") * rc_hz(val("12k") + val("2.7k"), "10n")),
        2500,
        rel=0.03,
    )
    s.text([f"Treble: half at {hz(f_mid)}", f"+/-{g_t:.1f} dB"], (x2 + 25.4, y + 50.8))

    # Fixed 12 kHz first-order low-pass that caps the treble boost.
    x3 = x2 + 55.88
    rl = s.part(R, "RX21", "1.3k", "chosen", "-", (x3 + 6.35, y + 2.54), rot=90, fields="above")
    cl = s.part(C, "CX9", "10n", "chosen", "-", (x3 + 12.7, y + 10.16), fields="right")
    s.wire(tout, rl["1"])
    s.wire(rl["2"], (x3 + 12.7, y + 2.54), cl["1"])
    s.gnd((x3 + 12.7, y + 16.51))
    s.wire(cl["2"], (x3 + 12.7, y + 16.51))
    s.wire((x3 + 12.7, y + 2.54), (x3 + 25.4, y + 2.54))
    s.hlabel("OUT", (x3 + 25.4, y + 2.54))
    f_top = expect("treble cap", rc_hz("1.3k", "10n"), 12000, rel=0.03)
    s.text(hz(f_top), (x3 + 2.54, y + 25.4))

    s.note(
        [
            "Section 7 of the circuit notes. The pedal's EQ circuit is not public; the DSP uses digital filters (fi.peak_eq_cq,",
            "fi.high_shelf, fi.lowpass), and this sheet is a standard analogue realisation of them, all chosen.",
            "Bass: graphic-EQ boost/cut band, 110 Hz, Q 0.9, +/-12 dB (bassF, bassQ). LX1, LX2 are simulated inductors (gyrators).",
            "Scoop: fixed -6 dB notch at 350 Hz, Q 0.7 (scoopF, scoopQ, scoopDB), reported by measurement [6].",
            "Treble: a first-order shelf with the same pot arrangement; the DSP's shelf is third-order, so it is steeper.",
            "RX21, CX9: fixed 12 kHz low-pass (topLP) so a full treble boost peaks broadly in the upper treble.",
        ]
    )
    return s


def level(p):
    s = p.sheet(9, "Level", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("9 Level")
    s.hlabel("IN", (40.64, 63.5), 180)
    pot = s.part(POT, "RVX5", "100k log (Level)", "chosen", "-", (58.42, 76.2), fields="left")
    s.wire((40.64, 63.5), (58.42, 63.5), pot["1"])
    s.wire(pot["3"], (58.42, 88.9))
    s.glabel("VB", (58.42, 88.9), 270)
    u = s.part(OPAMP, "UX9", "OPAMP", "chosen", "-", (78.74, 78.74), fields="upright")
    s.opamp_power(u)
    s.wire(pot["2"], (66.04, 76.2), u["+"])
    rg = s.part(R, "RX22", "1k", "chosen", "-", (71.12, 101.6), fields="left")
    rf = s.part(R, "RX23", "3k", "chosen", "-", (83.82, 93.98), rot=90, fields="below")
    s.wire(u["-"], (71.12, 93.98), rg["1"])
    s.wire(rg["2"], (71.12, 111.76))
    s.glabel("VB", (71.12, 111.76), 270)
    s.wire((71.12, 93.98), rf["1"])
    s.wire(rf["2"], (96.52, 93.98), (96.52, 78.74))
    s.wire(u["5"], (96.52, 78.74))
    ro = s.part(R, "RX24", "1k", "inferred", "[1]", (106.68, 78.74), rot=90, fields="above")
    co = s.part(CP, "CX10", "10u", "chosen", "-", (121.92, 78.74), rot=90, fields="below")
    s.wire((96.52, 78.74), ro["1"])
    s.wire(ro["2"], co["1"])
    s.wire(co["2"], (137.16, 78.74))
    s.hlabel("OUT", (137.16, 78.74))
    g = expect("Level make-up gain (dB)", 20 * math.log10(1 + val("3k") / val("1k")), 12, rel=0.01)
    s.text(f"gain +{g:.0f} dB", (99.06, 101.6))
    s.text("1 kOhm output impedance", (99.06, 58.42))
    s.note(
        [
            "Section 9 of the circuit notes. The DSP's Level runs from -40 to +12 dB (chosen); here a volume pot RVX5",
            "and a fixed +12 dB stage, UX9 with RX22 and RX23 (chosen). RX24: the documented 1 kOhm output impedance [1]",
            "(as a series resistor, inferred). CX10: output coupling (chosen). The DSP's safety limiter has no counterpart.",
        ]
    )
    return s
