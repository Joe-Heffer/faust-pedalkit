# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""BassEras's modelled circuit, for tools/schematics/build.py.

No public schematic of the reference pedal was found, and its clipping stages
sit in a sealed module, so this is the circuit src/basseras.dsp implements,
drawn as standard analogue stages: every part is chosen, apart from the
documented input impedance and the EQ's documented frequencies and range.
Sheets are numbered and named after the stages listed in section 4 of
docs/basseras/circuit-notes.md; sources [n] are that file's source list.
Every corner, gain and Q is checked against the DSP constant it stands for
with expect(), so the drawing can't drift from the DSP.
"""

import math
import textwrap

import stages
from kicadsch import Project, expect, hz, lc_hz, rc_hz, val
from stages import CP, JACK, OPAMP, POT, RVAR, C, D, L, R, band, series

NOTE_WIDTH = 130  # characters; the title block starts at 175 mm
CAVEAT = "Modelled circuit (src/basseras.dsp), a stand-in; not a trace of the pedal"
SPDT = "Switch:SW_SPDT"


def note(s, lines):
    """The sheet's note, with each paragraph wrapped to fit beside the title block."""
    s.note([w for line in lines for w in textwrap.wrap(line, NOTE_WIDTH)])


def project():
    p = Project(
        "basseras",
        "BassEras",
        hardware="Tech 21 VT Bass DI",
        date="2026-10-28",
        caveat=CAVEAT,
    )
    sup = stages.supply(
        p,
        [
            "The pedal runs on a 9 V supply or phantom power (documented [1]). RX1, RX2, CX1: a half-supply bias rail VB",
            "for the single-supply op-amps (chosen; the usual arrangement, not described by any source).",
            "Every other sheet takes +9V, GND and VB from here.",
        ],
    )
    sheets = [
        input_buffer(p),
        subsonic(p),
        character(p),
        stage1(p),
        stage2(p),
        presence(p),
        speaker(p),
        blend(p),
        tone(p),
        level(p),
    ]
    root(p, sup, *sheets)
    return p


# ---------------------------------------------------------------------------
# Shared stand-ins


def sk_lp(s, x0, y, refs, values, out_label=None):
    """Unity-gain Sallen-Key low-pass from (x0, y): f = 1/(2 pi R sqrt(Cf Cg)),
    Q = sqrt(Cf/Cg)/2 with equal resistors. Returns the output point."""
    ran, rbn, cgn, cfn, un = refs
    rv, cgv, cfv = values
    ra = s.part(R, ran, rv, "chosen", "-", (x0 + 10.16, y), rot=90, fields="below")
    rb = s.part(R, rbn, rv, "chosen", "-", (x0 + 30.48, y), rot=90, fields="above")
    u = s.part(OPAMP, un, "OPAMP", "chosen", "-", (x0 + 53.34, y + 2.54), fields="upright")
    s.opamp_power(u)
    cg = s.part(C, cgn, cgv, "chosen", "-", (x0 + 38.1, y + 7.62), fields="left")
    cf = s.part(C, cfn, cfv, "chosen", "-", (x0 + 40.64, y - 22.86), rot=90, fields="above")
    out = (x0 + 71.12, y + 2.54)
    s.wire((x0, y), ra["1"])
    s.wire(ra["2"], (x0 + 20.32, y), rb["1"])
    s.wire(rb["2"], (x0 + 38.1, y), u["+"])
    s.wire((x0 + 38.1, y), cg["1"])
    s.gnd((x0 + 38.1, y + 15.24))
    s.wire(cg["2"], (x0 + 38.1, y + 15.24))
    s.wire((x0 + 20.32, y), (x0 + 20.32, y - 22.86), cf["1"])
    s.wire(cf["2"], (out[0], y - 22.86), out)
    s.wire(u["-"], (x0 + 45.72, y + 20.32), (out[0], y + 20.32), out)
    s.wire(u["5"], out)
    return out


def sk_hp(s, x0, y, refs, values, rlib=R):
    """Unity-gain Sallen-Key high-pass from (x0, y), equal capacitors:
    f = 1/(2 pi C sqrt(Rf Rg)), Q = sqrt(Rg/Rf)/2. Rg returns to VB.
    Returns the output point."""
    can, cbn, rgn, rfn, un = refs
    cv, rgv, rfv = values
    ca = s.part(C, can, cv, "chosen", "-", (x0 + 10.16, y), rot=90, fields="below")
    cb = s.part(C, cbn, cv, "chosen", "-", (x0 + 30.48, y), rot=90, fields="above")
    u = s.part(OPAMP, un, "OPAMP", "chosen", "-", (x0 + 53.34, y + 2.54), fields="upright")
    s.opamp_power(u)
    rg = s.part(rlib, rgn, rgv, "chosen", "-", (x0 + 38.1, y + 7.62), fields="left")
    rf = s.part(rlib, rfn, rfv, "chosen", "-", (x0 + 40.64, y - 22.86), rot=90, fields="above")
    out = (x0 + 71.12, y + 2.54)
    s.wire((x0, y), ca["1"])
    s.wire(ca["2"], (x0 + 20.32, y), cb["1"])
    s.wire(cb["2"], (x0 + 38.1, y), u["+"])
    s.wire((x0 + 38.1, y), rg["1"])
    s.wire(rg["2"], (x0 + 38.1, y + 15.24))
    s.glabel("VB", (x0 + 38.1, y + 15.24), 270)
    s.wire((x0 + 20.32, y), (x0 + 20.32, y - 22.86), rf["1"])
    s.wire(rf["2"], (out[0], y - 22.86), out)
    s.wire(u["-"], (x0 + 45.72, y + 20.32), (out[0], y + 20.32), out)
    s.wire(u["5"], out)
    return out


def sk_lp_check(what, r, cf, cg, f, q):
    fa = expect(f"{what} corner", 1 / (2 * math.pi * val(r) * math.sqrt(val(cf) * val(cg))), f)
    qa = expect(f"{what} Q", 0.5 * math.sqrt(val(cf) / val(cg)), q, rel=0.02)
    return fa, qa


def sk_hp_check(what, c, rg, rf, f, q, rel=0.05):
    fa = expect(f"{what} corner", 1 / (2 * math.pi * val(c) * math.sqrt(val(rg) * val(rf))), f, rel)
    qa = expect(f"{what} Q", 0.5 * math.sqrt(val(rg) / val(rf)), q, rel=0.02)
    return fa, qa


def gain_stage(s, x0, y, refs, values, confs=None):
    """Non-inverting op-amp stage from (x0, y): gain 1 + Rf/Rg, Rg to VB, Rf
    from the output. values = (Rg, Rf); Rf can be a variable resistor (a
    (lib, value) pair). Returns (output point, op-amp)."""
    rgn, rfn, un = refs
    rgv, rfv = values
    rflib, rfv = rfv if isinstance(rfv, tuple) else (R, rfv)
    u = s.part(OPAMP, un, "OPAMP", "chosen", "-", (x0 + 20.32, y + 2.54), fields="upright")
    s.opamp_power(u)
    s.wire((x0, y), u["+"])
    rg = s.part(R, rgn, rgv, "chosen", "-", (x0 + 5.08, y + 15.24), fields="left")
    rf = s.part(rflib, rfn, rfv, "chosen", "-", (x0 + 22.86, y + 22.86), rot=90, fields="below")
    out = (x0 + 38.1, y + 2.54)
    s.wire(u["-"], (x0 + 7.62, y + 5.08), (x0 + 5.08, y + 5.08), rg["1"])
    s.wire(rg["2"], (x0 + 5.08, y + 22.86))
    s.glabel("VB", (x0 + 5.08, y + 33.02), 270)
    s.wire((x0 + 5.08, y + 22.86), (x0 + 5.08, y + 33.02))
    s.wire((x0 + 5.08, y + 22.86), rf["1"])
    s.wire(rf["2"], (out[0], y + 22.86), out)
    s.wire(u["5"], out)
    return out, u


# ---------------------------------------------------------------------------


def root(p, sup, buf, sub, char, st1, st2, bite_p, spk, bl, eq_, lvl):
    s = p.root
    s.heading("BassEras: modelled circuit")
    s.text(
        [
            "Block diagram of section 4 of docs/basseras/circuit-notes.md: one sub-sheet per stage of src/basseras.dsp, numbered",
            "and named after the list there. No schematic of the reference pedal is public and its clipping stages are a sealed",
            "module, so every stage is a standard analogue stand-in for the DSP, not a trace of the pedal.",
        ],
        (25.4, 40.64),
    )
    y1, y2, y3 = 58.42, 99.06, 139.7
    b2 = p.block(buf, (40.64, y1))
    b3 = p.block(sub, (91.44, y1))
    b4 = p.block(char, (142.24, y1))
    b5 = p.block(st1, (193.04, y1))
    b6 = p.block(st2, (40.64, y2))
    b7 = p.block(bite_p, (91.44, y2))
    b8 = p.block(spk, (142.24, y2))
    b9 = p.block(bl, (193.04, y2))
    b10 = p.block(eq_, (40.64, y3))
    b11 = p.block(lvl, (91.44, y3))
    p.block(sup, (142.24, y3), (38.1, 15.24))

    j1 = s.part(JACK, "JX1", "Input", "documented", "[1]", (25.4, 63.5), fields="above", mirror="x")
    s.wire(j1["T"], b2["IN"])
    s.wire(j1["S"], (33.02, j1["S"][1]), (33.02, 71.12))
    s.gnd((33.02, 71.12))
    s.wire(b2["OUT"], b3["IN"])
    s.wire(b3["OUT"], b4["IN"])
    s.wire(b4["OUT"], b5["IN"])
    # Long hops between rows go by global label.
    hops = [
        ("STAGE1", b5["OUT"], b6["IN"]),
        ("MIX", b9["OUT"], b10["IN"]),
    ]
    for name, a, b in hops:
        xa = a[0] + 5.08
        s.wire(a, (xa, a[1]))
        s.glabel(name, (xa, a[1]), 0)
        xb = b[0] - 5.08
        s.glabel(name, (xb, b[1]), 180)
        s.wire((xb, b[1]), b)
    s.wire(b6["OUT"], b7["IN"])
    s.wire(b7["OUT"], b8["IN"])
    s.wire(b8["OUT"], b9["DRIVEN"])
    # The clean side of the blend, from the input buffer.
    xc = b2["OUT"][0] + 5.08
    s.wire((xc, b2["OUT"][1]), (xc, 86.36))
    s.glabel("CLEAN", (xc, 86.36), 270)
    xd = b9["CLEAN"][0] - 5.08
    s.wire(b9["CLEAN"], (xd, b9["CLEAN"][1]), (xd, y2 + 30.48))
    s.glabel("CLEAN", (xd, y2 + 30.48), 270)
    s.wire(b10["OUT"], b11["IN"])
    j2 = s.part(
        JACK, "JX2", "Output", "documented", "[1]", (154.94, 172.72), rot=180, fields="above"
    )
    s.wire(b11["OUT"], (137.16, b11["OUT"][1]), (137.16, 165.1), (j2["T"][0], 165.1), j2["T"])
    s.wire(j2["S"], (j2["S"][0] - 5.08, j2["S"][1]), (j2["S"][0] - 5.08, 180.34))
    s.gnd((j2["S"][0] - 5.08, 180.34))
    s.text(
        [
            "In the DSP the clean path is delayed by 64 samples to line up with the two",
            "4x oversamplers; that delay has no circuit counterpart.",
        ],
        (25.4, 172.72),
    )


def input_buffer(p):
    s = p.sheet(2, "Input buffer", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("2 Input buffer")
    s.hlabel("IN", (38.1, 76.2), 180)
    c = s.part(C, "CX2", "33n", "chosen", "-", (48.26, 76.2), rot=90, fields="above")
    r = s.part(R, "RX3", "1M", "documented", "[1]", (66.04, 83.82), fields="left")
    u = s.part(OPAMP, "UX1", "OPAMP", "chosen", "-", (88.9, 78.74), fields="upright")
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
    s.text([f"CX2 with RX3: {hz(f)}", "(DSP: 5 Hz DC blocker)"], (45.72, 106.68))
    note(
        s,
        [
            "Section 4 of the circuit notes, stage 2. RX3: the documented 1 MOhm input impedance [1], drawn as the bias resistor to VB.",
            "CX2: input coupling, chosen with RX3 for the DSP's 5 Hz DC blocker. UX1: a unity-gain buffer (chosen). Its output feeds",
            "both the preamp path and the clean side of the Blend (CLEAN on the root sheet).",
        ],
    )
    return s


def subsonic(p):
    s = p.sheet(3, "Bite subsonic filter", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("3 Bite: subsonic filter")
    s.hlabel("IN", (30.48, 81.28), 180)
    s.wire((30.48, 81.28), (40.64, 81.28))
    out = sk_hp(
        s,
        40.64,
        81.28,
        ("CX3", "CX4", "RVX1", "RVX2", "UX2"),
        ("100n", "56.3k (Bite)", "28.1k (Bite)"),
        rlib=RVAR,
    )
    s.wire(out, (out[0] + 12.7, out[1]))
    s.hlabel("OUT", (out[0] + 12.7, out[1]))
    f40, q = sk_hp_check("Bite 100 subsonic", "100n", "56.3k", "28.1k", 40, 0.707)
    f10, _ = sk_hp_check("Bite 0 subsonic", "100n", "225k", "113k", 10, 0.707)
    s.text(
        [
            f"Bite 100: {hz(f40)}, Q {q:.2f}; Bite 0: {hz(f10)}",
            "RVX1, RVX2: two gangs of one pot, shown at Bite 100;",
            "each is 4 times larger at Bite 0 (225k, 113k)",
        ],
        (40.64, 116.84),
    )
    note(
        s,
        [
            "Section 4 of the circuit notes, stage 3. The pedal's Bite switch adds a subsonic filter [1]; its circuit is not public.",
            "A unity-gain Sallen-Key Butterworth high-pass (all chosen) whose resistors are two gangs of the Bite pot, so the corner",
            "glides from 10 Hz (Bite 0, out of the way) to 40 Hz (Bite 100, just below low E) at a constant Q, as biteHpLo and biteHpHi",
            "do in the DSP. A switch and fixed resistors would give the pedal's two settings.",
        ],
    )
    return s


def character(p):
    s = p.sheet(4, "Character", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("4 Character: pre-clip mid EQ and gain")
    y, x0 = 66.04, 27.94
    s.hlabel("IN", (20.32, y), 180)
    bin_, bout, bw = band(
        s, x0, y, ("RX4", "RVX3", "RX5", "UX3"), ("4.7k", "100k (Character)", "4.7k", "OPAMP")
    )
    s.wire((20.32, y), bin_)
    series(s, bw[0], bw[1], [(R, "RX6", "1k"), (L, "LX1", "636mH"), (C, "CX5", "228n")])
    f_c = expect("Character centre at noon", lc_hz("636m", "228n"), math.sqrt(250 * 700), rel=0.01)
    g_c = expect(
        "Character range", 20 * math.log10((val("4.7k") + val("1k")) / val("1k")), 15, rel=0.02
    )
    w0 = 2 * math.pi * f_c
    q_c = expect(
        "Character Q", w0 * val("636m") / math.sqrt(val("1k") * (val("4.7k") + val("1k"))), 0.7
    )
    s.text([f"centre {hz(f_c)} at noon, Q {q_c:.2f}", f"+/-{g_c:.0f} dB"], (x0 + 22.86, y + 50.8))
    # Extra gain above noon: a second gang of the Character pot.
    x1 = x0 + 66.04
    s.wire(bout, (x1, bout[1]))
    out, _ = gain_stage(s, x1, bout[1], ("RX7", "RVX4", "UX4"), ("1k", (RVAR, "3k (Character)")))
    g_x = expect("Character extra gain (dB)", 20 * math.log10(1 + val("3k") / val("1k")), 12, 0.01)
    s.wire(out, (out[0] + 12.7, out[1]))
    s.hlabel("OUT", (out[0] + 12.7, out[1]))
    s.text(f"0 to +{g_x:.0f} dB (charGainDb)", (x1 + 12.7, bout[1] + 45.72))
    note(
        s,
        [
            "Section 4 of the circuit notes, stage 4. A pre-clip mid boost or cut of about +/-15 dB is reported for the series [3];",
            "its circuit is not public. UX3: a graphic-EQ band (chosen) at +/-15 dB (charRange); LX1 is a simulated inductor (gyrator).",
            "Drawn at noon: the DSP also glides the centre from 250 Hz (Character 0) to 700 Hz (Character 100) at Q 0.7, which a second",
            "gang in the gyrator would do. UX4 with RVX4: the extra gain of up to 12 dB above noon (charGainDb, chosen; the manual [1] says",
            "Character adds gain above noon). RVX4 is a further gang, at 0 Ohm from Character 0 to 50.",
        ],
    )
    return s


def stage1(p):
    s = p.sheet(5, "Stage 1", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("5 Stage 1: Drive and soft clip")
    y = 71.12
    s.hlabel("IN", (30.48, y), 180)
    s.wire((30.48, y), (40.64, y))
    out, _ = gain_stage(s, 40.64, y, ("RX8", "RVX5", "UX5"), ("1k", (RVAR, "30.6k log (Drive)")))
    g = expect("Drive range (dB)", 20 * math.log10(1 + val("30.6k") / val("1k")), 30, rel=0.01)
    # Soft clip: a series resistor into two strings of two diodes to VB.
    rs = s.part(R, "RX9", "1k", "chosen", "-", (out[0] + 10.16, out[1]), rot=90, fields="above")
    s.wire(out, rs["1"])
    left = rs["2"][0] + 5.08
    right = left + 25.4
    s.wire(rs["2"], (left, out[1]))
    y1, y2 = out[1] + 10.16, out[1] + 22.86
    d = [
        s.part(D, "DX1", "1N4148", "chosen", "-", (left + 6.35, y1), fields="above"),
        s.part(D, "DX2", "1N4148", "chosen", "-", (left + 19.05, y1), fields="above"),
        s.part(D, "DX3", "1N4148", "chosen", "-", (left + 6.35, y2), rot=180, fields="below"),
        s.part(D, "DX4", "1N4148", "chosen", "-", (left + 19.05, y2), rot=180, fields="below"),
    ]
    s.wire((left, out[1]), (left, y2))
    for a, b, (first, second) in ((d[0], d[1], ("K", "A")), (d[2], d[3], ("A", "K"))):
        yy = a[first][1]
        s.wire((left, yy), a[first])
        s.wire(a[second], b[first])
        s.wire(b[second], (right, yy))
    s.wire((right, y1), (right, y2), (right, y2 + 5.08))
    s.glabel("VB", (right, y2 + 5.08), 270)
    # Inter-stage low-pass.
    rl = s.part(R, "RX10", "2.7k", "chosen", "-", (right + 12.7, out[1]), rot=90, fields="above")
    cl = s.part(C, "CX6", "10n", "chosen", "-", (right + 20.32, out[1] + 7.62), fields="right")
    s.wire((left, out[1]), rl["1"])
    s.wire(rl["2"], (right + 20.32, out[1]), cl["1"])
    s.gnd((right + 20.32, out[1] + 15.24))
    s.wire(cl["2"], (right + 20.32, out[1] + 15.24))
    s.wire((right + 20.32, out[1]), (right + 33.02, out[1]))
    s.hlabel("OUT", (right + 33.02, out[1]))
    f_lp = expect("inter-stage low-pass", rc_hz("2.7k", "10n"), 6000, rel=0.03)
    s.text(f"0 to {g:.0f} dB (driveMaxDb)", (53.34, y + 45.72))
    s.text(["about +/-1.2 V", "(v1, two diode drops)"], (left, y2 + 20.32))
    s.text(f"RX10 with CX6: {hz(f_lp)} (interLp)", (right + 5.08, out[1] - 17.78))
    note(
        s,
        [
            "Section 4 of the circuit notes, stage 5. The series' module is reported to have two gain stages [3]; their circuits are not public.",
            "UX5 with RVX5: the Drive gain, 0 to 30 dB log-uniform (driveMaxDb, chosen). RX9 and DX1 to DX4: a soft clip at about two",
            "diode drops, standing in for the DSP's tanh at +/-1.2 V (v1, chosen). RX10, CX6: the 6 kHz inter-stage low-pass (interLp, chosen).",
        ],
    )
    return s


def stage2(p):
    s = p.sheet(6, "Stage 2 and bloom", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("6 Stage 2: rail clip with the bias bloom")
    y = 71.12
    s.hlabel("IN", (25.4, y), 180)
    ri = s.part(R, "RX11", "10k", "chosen", "-", (35.56, y), rot=90, fields="above")
    s.wire((25.4, y), ri["1"])
    s.wire(ri["2"], (50.8, y))
    out, u = gain_stage(s, 50.8, y, ("RX12", "RX13", "UX6"), ("1k", "3k"))
    g = expect("stage 2 gain", 1 + val("3k") / val("1k"), 4)
    # Output coupling, after the clipping stage.
    co = s.part(CP, "CX7", "1u", "chosen", "-", (out[0] + 12.7, out[1]), rot=90, fields="above")
    ro = s.part(R, "RX14", "33k", "chosen", "-", (out[0] + 25.4, out[1] + 7.62), fields="right")
    s.wire(out, co["1"])
    s.wire(co["2"], (out[0] + 25.4, out[1]), ro["1"])
    s.wire(ro["2"], (out[0] + 25.4, out[1] + 15.24))
    s.glabel("VB", (out[0] + 25.4, out[1] + 15.24), 270)
    s.wire((out[0] + 25.4, out[1]), (out[0] + 38.1, out[1]))
    s.hlabel("OUT", (out[0] + 38.1, out[1]))
    # Bloom: peak detector on the stage's output, scaled by Character, summed
    # into the + input.
    yb = y + 50.8
    dx = s.part(D, "DX5", "1N4148", "chosen", "-", (out[0], yb - 12.7), rot=270, fields="right")
    s.wire(out, dx["A"])
    ra = s.part(R, "RX15", "20k", "chosen", "-", (out[0], yb + 2.54), fields="right")
    s.wire(dx["K"], ra["1"])
    node = (out[0], yb + 12.7)
    s.wire(ra["2"], node)
    ch = s.part(CP, "CX8", "1u", "chosen", "-", (out[0] + 10.16, yb + 20.32), fields="right")
    rr = s.part(R, "RX16", "150k", "chosen", "-", (out[0] + 22.86, yb + 20.32), fields="right")
    s.wire(node, (out[0] + 22.86, node[1]), rr["1"])
    s.wire((out[0] + 10.16, node[1]), ch["1"])
    for part in (ch, rr):
        s.wire(part["2"], (part["2"][0], yb + 30.48))
        s.glabel("VB", (part["2"][0], yb + 30.48), 270)
    pot = s.part(
        POT,
        "RVX6",
        "100k (Character, above noon)",
        "chosen",
        "-",
        (out[0] - 17.78, node[1]),
        rot=90,
        fields="below",
    )
    near, far = (pot["3"], pot["1"]) if pot["3"][0] > pot["1"][0] else (pot["1"], pot["3"])
    s.wire(node, near)
    s.wire(far, (far[0] - 5.08, far[1]), (far[0] - 5.08, yb + 30.48))
    s.glabel("VB", (far[0] - 5.08, yb + 30.48), 270)
    xs = 40.64
    rsum = s.part(R, "RX17", "33k", "chosen", "-", (xs, y + 15.24), fields="left")
    s.wire((xs, y), rsum["1"])
    s.wire(pot["2"], (pot["2"][0], pot["2"][1] - 5.08), (xs, pot["2"][1] - 5.08), rsum["2"])
    t_att = expect("bloom attack (s)", val("20k") * val("1u"), 0.02)
    t_rel = expect("bloom release (s)", val("150k") * val("1u"), 0.15)
    f_dc = expect("output DC block", rc_hz("33k", "1u"), 5.0)
    s.text(
        [f"gain {g:g} (g2), clips at the rails:", "about +/-3.1 V on 9 V (railV, inferred)"],
        (50.8, y - 20.32),
    )
    s.text(
        [f"attack {1000 * t_att:.0f} ms (bloomAtt)", f"release {1000 * t_rel:.0f} ms (bloomRel)"],
        (out[0] + 27.94, yb + 2.54),
    )
    s.text(f"CX7 with RX14: {hz(f_dc)}", (out[0] + 33.02, y - 7.62))
    note(
        s,
        [
            "Section 4 of the circuit notes, stage 6. UX6 with RX12, RX13: the second gain stage, gain 4 (g2, chosen). The series' module",
            "is reported to clip with 3.3 V zeners in this stage's feedback [3]; on a 9 V supply the rails clip first (inferred, open question 2),",
            "so UX6 clips at its rails. DX5, RX15, CX8, RX16: a peak detector that charges on hard notes (20 ms) and recovers (150 ms);",
            "RVX6, a gang of the Character pot that is at 0 up to noon, feeds a share of it to the + input through RX17, moving the",
            "stage off centre (bloomMax, chosen, the design notes' departure). CX7, RX14: the 5 Hz DC block after the clipping.",
        ],
    )
    return s


def presence(p):
    s = p.sheet(7, "Bite presence", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("7 Bite: presence boost")
    y, x0 = 66.04, 40.64
    s.hlabel("IN", (30.48, y), 180)
    bin_, bout, bw = band(
        s, x0, y, ("RX18", "RVX7", "RX19", "UX7"), ("2.2k", "100k (Bite)", "2.2k", "OPAMP")
    )
    s.wire((30.48, y), bin_)
    series(s, bw[0], bw[1], [(R, "RX20", "2.2k"), (L, "LX2", "139mH"), (C, "CX9", "29.2n")])
    f_p = expect("presence centre", lc_hz("139m", "29.2n"), 2500, rel=0.02)
    g_p = expect(
        "presence boost (dB)", 20 * math.log10((val("2.2k") + val("2.2k")) / val("2.2k")), 6, 0.01
    )
    w0 = 2 * math.pi * f_p
    q_p = expect(
        "presence Q", w0 * val("139m") / math.sqrt(val("2.2k") * (val("2.2k") * 2)), 0.7, 0.02
    )
    s.wire(bout, (bout[0] + 12.7, bout[1]))
    s.hlabel("OUT", (bout[0] + 12.7, bout[1]))
    s.text([f"{hz(f_p)}, Q {q_p:.2f}", f"0 to +{g_p:.0f} dB"], (x0 + 22.86, y + 50.8))
    note(
        s,
        [
            "Section 4 of the circuit notes, stage 7. The pedal's Bite switch adds a presence boost [1]; its circuit is not public.",
            "UX7: a graphic-EQ band (chosen), +6 dB at 2.5 kHz, Q 0.7 (presF, presDb, presQ). LX2 is a simulated inductor (gyrator).",
            "RVX7 runs from its centre (flat, Bite 0) to the boost end (Bite 100); the pedal's switch would select the two ends.",
        ],
    )
    return s


def speaker(p):
    s = p.sheet(8, "Speaker sim", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("8 Speaker sim and Cab Bypass")
    y = 71.12
    s.hlabel("IN", (20.32, y), 180)
    s.wire((20.32, y), (27.94, y))
    o1 = sk_lp(s, 27.94, y, ("RX21", "RX22", "CX10", "CX11", "UX8"), ("10k", "2.5n", "5n"))
    s.wire(o1, (o1[0] + 10.16, o1[1]))
    o2 = sk_lp(
        s, o1[0] + 10.16, o1[1], ("RX23", "RX24", "CX12", "CX13", "UX9"), ("10k", "2.21n", "3.18n")
    )
    y2 = y + 66.04
    s.wire(
        o2,
        (o2[0] + 5.08, o2[1]),
        (o2[0] + 5.08, y2 - 33.02),
        (20.32, y2 - 33.02),
        (20.32, y2),
        (27.94, y2),
    )
    o3 = sk_hp(s, 27.94, y2, ("CX14", "CX15", "RX25", "RX26", "UX10"), ("100n", "63.7k", "44.2k"))
    # Cab Bypass: the common pin takes the voiced or the unfiltered signal.
    sw = s.part(
        SPDT,
        "SWX1",
        "Cab Bypass",
        "chosen",
        "-",
        (o3[0] + 30.48, o3[1]),
        fields="above",
        mirror="y",
    )
    voiced, bypass = (sw["1"], sw["3"]) if sw["1"][1] < sw["3"][1] else (sw["3"], sw["1"])
    s.wire(o3, (voiced[0] - 7.62, o3[1]), (voiced[0] - 7.62, voiced[1]), voiced)
    # The unfiltered signal reaches the switch by label rather than a long wire.
    s.wire((20.32, y), (20.32, y - 10.16))
    s.glabel("CAB_DRY", (20.32, y - 10.16), 90)
    s.wire(bypass, (bypass[0] - 5.08, bypass[1]))
    s.glabel("CAB_DRY", (bypass[0] - 5.08, bypass[1]), 180)
    s.wire(sw["2"], (sw["2"][0] + 10.16, sw["2"][1]))
    s.hlabel("OUT", (sw["2"][0] + 10.16, sw["2"][1]))
    f1, q1 = sk_lp_check("speaker low-pass 1", "10k", "5n", "2.5n", 4500, 0.707)
    f2, q2 = sk_lp_check("speaker low-pass 2", "10k", "3.18n", "2.21n", 6000, 0.6)
    f3, q3 = sk_hp_check("speaker high-pass", "100n", "63.7k", "44.2k", 30, 0.6)
    s.text(f"{hz(f1)}, Q {q1:.2f}", (27.94 + 50.8, y + 25.4))
    s.text(f"{hz(f2)}, Q {q2:.2f}", (o1[0] + 10.16 + 50.8, y + 25.4))
    s.text(f"{hz(f3)}, Q {q3:.2f}", (27.94 + 50.8, y2 + 25.4))
    note(
        s,
        [
            "Section 4 of the circuit notes, stage 8. A two-stage high-frequency roll-off is reported for the series [3], and the pedal's",
            "speaker sim is documented as smooth, without peaks or notches [1]; its circuit is not public. UX8, UX9: two unity-gain Sallen-Key",
            "low-passes, -3 dB together at about 3.7 kHz with no peak; UX10: a 30 Hz high-pass for the cabinet's low end (all chosen).",
            "SWX1: Cab Bypass (not on the pedal). In the DSP it crossfades between the voiced and the unfiltered signal; drawn as a switch.",
        ],
    )
    return s


def blend(p):
    s = p.sheet(9, "Blend", pins=[("DRIVEN", "input"), ("CLEAN", "input"), ("OUT", "output")])
    s.heading("9 Blend")
    s.hlabel("CLEAN", (40.64, 63.5), 180)
    s.hlabel("DRIVEN", (40.64, 93.98), 180)
    ra = s.part(R, "RX27", "8.5k", "chosen", "-", (53.34, 93.98), rot=90, fields="below")
    rb = s.part(R, "RX28", "1k", "chosen", "-", (63.5, 104.14), fields="right")
    s.wire((40.64, 93.98), ra["1"])
    s.wire(ra["2"], (63.5, 93.98), rb["1"])
    s.wire(rb["2"], (63.5, 111.76))
    s.glabel("VB", (63.5, 111.76), 270)
    pot = s.part(POT, "RVX8", "100k lin (Blend)", "chosen", "-", (88.9, 78.74), fields="left")
    s.wire((40.64, 63.5), (88.9, 63.5), pot["1"])
    s.wire((63.5, 93.98), (88.9, 93.98), pot["3"])
    u = s.part(OPAMP, "UX11", "OPAMP", "chosen", "-", (110.49, 81.28), fields="upright")
    s.opamp_power(u)
    s.wire(pot["2"], u["+"])
    s.wire(u["-"], (102.87, 101.6), (124.46, 101.6), (124.46, 81.28))
    s.wire(u["5"], (124.46, 81.28), (137.16, 81.28))
    s.hlabel("OUT", (137.16, 81.28))
    trim = expect(
        "driven-path trim (drvTrim / g2)", val("1k") / (val("8.5k") + val("1k")), 0.42 / 4, 0.01
    )
    s.text(f"x{trim:.3f} (drvTrim / g2)", (45.72, 124.46))
    s.text(
        ["wiper = clean + b (driven - clean)", "b = 0 clean only, 1 preamp only"], (129.54, 68.58)
    )
    note(
        s,
        [
            "Section 4 of the circuit notes, stage 9. The Blend is documented [1]; its circuit is not public. RVX8, UX11: a linear crossfade",
            "(chosen), which gives the DSP's blend exactly. RX27, RX28: the preamp path's trim, drvTrim / g2 = 0.105 (chosen, set by measurement",
            "so that the preamp path matches the clean level at the defaults); their 0.9 kOhm source impedance bends the pot's law slightly.",
        ],
    )
    return s


def tone(p):
    s = p.sheet(10, "Low Mid High", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("10 Low, Mid and High")
    y = 60.96
    x0 = 27.94
    s.hlabel("IN", (20.32, y), 180)
    vals = ("3k", "100k", "3k", "OPAMP")
    lin, lout, lw = band(
        s, x0, y, ("RX29", "RVX9", "RX30", "UX12"), (vals[0], "100k (Low)", *vals[2:])
    )
    s.wire((20.32, y), lin)
    series(s, lw[0], lw[1], [(R, "RX31", "1k"), (L, "LX3", "2.55H")])
    g = expect("EQ range (dB)", 20 * math.log10((val("3k") + val("1k")) / val("1k")), 12, rel=0.01)
    f_low = expect(
        "Low shelf midpoint",
        math.sqrt(val("1k") * (val("3k") + val("1k"))) / (2 * math.pi * val("2.55")),
        125,
        rel=0.02,
    )
    s.text([f"Low: half at {hz(f_low)}", f"+/-{g:.0f} dB"], (x0 + 25.4, y + 50.8))

    x1 = x0 + 55.88
    min_, mout, mw = band(
        s, x1, y, ("RX32", "RVX10", "RX33", "UX13"), (vals[0], "100k (Mid)", *vals[2:])
    )
    s.wire(lout, (x1 + 1.27, lout[1]), (x1 + 1.27, y), min_)
    series(
        s,
        mw[0],
        mw[1],
        [
            (R, "RX34", "1k"),
            (L, "LX4", "223mH"),
            (C, "CX16", "114n"),
        ],
    )
    f_mid = expect("Mid centre", lc_hz("223m", "114n"), 1000, rel=0.02)
    q_mid = expect(
        "Mid Q", 2 * math.pi * f_mid * val("223m") / math.sqrt(val("1k") * val("4k")), 0.7, 0.02
    )
    s.text([f"Mid: {hz(f_mid)}, Q {q_mid:.2f}", f"+/-{g:.0f} dB"], (x1 + 25.4, y + 50.8))

    x2 = x1 + 55.88
    hin, hout, hw = band(
        s, x2, y, ("RX35", "RVX11", "RX36", "UX14"), (vals[0], "100k (High)", *vals[2:])
    )
    s.wire(mout, (x2 + 1.27, mout[1]), (x2 + 1.27, y), hin)
    series(s, hw[0], hw[1], [(R, "RX37", "1k"), (C, "CX17", "24.9n")])
    f_high = expect(
        "High shelf midpoint",
        math.sqrt(rc_hz("1k", "24.9n") * rc_hz(val("3k") + val("1k"), "24.9n")),
        3200,
        rel=0.02,
    )
    s.text([f"High: half at {hz(f_high)}", f"+/-{g:.0f} dB"], (x2 + 25.4, y + 50.8))
    s.wire(hout, (hout[0] + 12.7, hout[1]))
    s.hlabel("OUT", (hout[0] + 12.7, hout[1]))
    note(
        s,
        [
            "Section 4 of the circuit notes, stage 10. Documented [1]: +/-12 dB from unity at noon, Low at 125 Hz, Mid at 1 kHz, High at",
            "3.2 kHz; active Baxandall-style stages are reported for the series [3]. The circuits here are graphic-EQ bands (chosen) whose",
            "networks are set to those documented frequencies and that range. LX3, LX4: simulated inductors (gyrators). Low and High are",
            "first-order shelves here; the DSP's (pk.lowShelf2, pk.highShelf2) are second-order, so steeper.",
        ],
    )
    return s


def level(p):
    s = p.sheet(11, "Level", pins=[("IN", "input"), ("OUT", "output")])
    s.heading("11 Level")
    s.hlabel("IN", (40.64, 63.5), 180)
    pot = s.part(POT, "RVX12", "100k log (Level)", "chosen", "-", (58.42, 76.2), fields="left")
    s.wire((40.64, 63.5), (58.42, 63.5), pot["1"])
    s.wire(pot["3"], (58.42, 88.9))
    s.glabel("VB", (58.42, 88.9), 270)
    u = s.part(OPAMP, "UX15", "OPAMP", "chosen", "-", (78.74, 78.74), fields="upright")
    s.opamp_power(u)
    s.wire(pot["2"], (66.04, 76.2), u["+"])
    rg = s.part(R, "RX38", "1k", "chosen", "-", (71.12, 101.6), fields="left")
    rf = s.part(R, "RX39", "3k", "chosen", "-", (83.82, 93.98), rot=90, fields="below")
    s.wire(u["-"], (71.12, 93.98), rg["1"])
    s.wire(rg["2"], (71.12, 111.76))
    s.glabel("VB", (71.12, 111.76), 270)
    s.wire((71.12, 93.98), rf["1"])
    s.wire(rf["2"], (96.52, 93.98), (96.52, 78.74))
    s.wire(u["5"], (96.52, 78.74))
    co = s.part(CP, "CX18", "10u", "chosen", "-", (111.76, 78.74), rot=90, fields="below")
    s.wire((96.52, 78.74), co["1"])
    s.wire(co["2"], (127, 78.74))
    s.hlabel("OUT", (127, 78.74))
    g = expect("Level make-up gain (dB)", 20 * math.log10(1 + val("3k") / val("1k")), 12, rel=0.01)
    s.text(f"gain +{g:.0f} dB", (99.06, 101.6))
    note(
        s,
        [
            "Section 4 of the circuit notes, stage 11. The DSP's Level runs from -40 to +12 dB (chosen): here a volume pot RVX12 and a fixed",
            "+12 dB stage, UX15 with RX38 and RX39 (chosen). CX18: output coupling (chosen). The DSP's safety limiter has no counterpart.",
        ],
    )
    return s
