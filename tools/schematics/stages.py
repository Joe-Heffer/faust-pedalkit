# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Building blocks shared by the effect schematics in tools/schematics/.

Stock KiCad symbols by short name, the supply-and-bias sheet every project
starts with, and the analogue stand-ins for digital filters (a graphic-EQ
boost/cut band and a series chain to ground).
"""

OPAMP = "Simulation_SPICE:OPAMP"
R, C, CP, L = "Device:R", "Device:C", "Device:C_Polarized", "Device:L"
POT, RVAR = "Device:R_Potentiometer", "Device:R_Variable"
LED, D = "Device:LED", "Device:D"
SW = "Switch:SW_SPST"
JACK = "Connector_Audio:AudioJack2"


def supply(p, note, vb="VB = 4.5 V", supply_conf=("chosen", "-")):
    """Sheet 1: the 9 V supply with its power flags, and a half-supply bias
    rail VB (RX1, RX2, CX1) as a global label for the other sheets."""
    s = p.sheet(1, "Supply and bias")
    s.heading("1 Supply and bias")
    s.supply((60.96, 60.96))
    s.pwr_flag((50.8, 60.96))
    s.wire((50.8, 60.96), (60.96, 60.96))
    r1 = s.part(R, "RX1", "10k", *supply_conf, (60.96, 71.12), fields="left")
    r2 = s.part(R, "RX2", "10k", *supply_conf, (60.96, 91.44), fields="left")
    c1 = s.part(CP, "CX1", "10u", "chosen", "-", (76.2, 91.44))
    s.wire((60.96, 60.96), r1["1"])
    s.wire(r1["2"], (60.96, 81.28), r2["1"])
    s.wire((60.96, 81.28), (76.2, 81.28), c1["1"])
    s.wire((76.2, 81.28), (91.44, 81.28))
    s.glabel("VB", (91.44, 81.28))
    s.gnd((60.96, 101.6))
    s.wire(r2["2"], (60.96, 101.6))
    s.gnd((76.2, 101.6))
    s.wire(c1["2"], (76.2, 101.6))
    s.pwr_flag((45.72, 96.52))
    s.gnd((45.72, 101.6))
    s.wire((45.72, 96.52), (45.72, 101.6))
    s.text(vb, (93.98, 77.47))
    s.note(note)
    return s


def band(s, x0, y, refs, values, conf=("chosen", "-")):
    """A boost/cut band as in a graphic EQ: input through R1 to the + input,
    a pot from there to the - input, R2 back to the output, and a series
    network from the wiper to ground. With the wiper at the + end the network
    shunts the input (cut); at the - end it shunts the feedback (boost); in
    the middle the band is flat. The peak gain is (R2 + Rs) / Rs, where Rs is
    the network's resistance at its tuned frequency.
    Returns (input, output, wiper)."""
    r1n, potn, r2n, un = refs
    r1v, potv, r2v, uv = values
    u = s.part(OPAMP, un, uv, *conf, (x0 + 33.02, y + 2.54), fields="upright")
    s.opamp_power(u)
    r1 = s.part(R, r1n, r1v, *conf, (x0 + 7.62, y), rot=90, fields="above")
    pot = s.part(POT, potn, potv, *conf, (x0 + 19.05, y + 20.32), rot=270, fields="left")
    r2 = s.part(R, r2n, r2v, *conf, (x0 + 31.75, y + 30.48), rot=90, fields="below")
    s.wire(r1["2"], (x0 + 15.24, y), u["+"])
    s.wire((x0 + 15.24, y), pot["3"])
    s.wire(u["-"], (x0 + 22.86, y + 5.08), (x0 + 22.86, y + 30.48), r2["1"])
    out = (x0 + 50.8, y + 2.54)
    s.wire(r2["2"], (out[0], y + 30.48), out)
    s.wire(u["5"], out)
    return r1["1"], out, pot["2"]


def series(s, x, y, parts, ground=True):
    """Parts in a vertical chain from (x, y) downwards, 11.43 mm apart, each
    (lib, ref, value) or (lib, ref, value, confidence, source). Ends on a
    ground symbol, or returns the last pin when ground is False."""
    prev = (x, y)
    for i, spec in enumerate(parts):
        lib, ref, value, *cs = spec
        conf = cs or ("chosen", "-")
        part = s.part(lib, ref, value, *conf, (x, y + 10.16 + i * 11.43), fields="left")
        s.wire(prev, part["1"])
        prev = part["2"]
    if not ground:
        return prev
    gnd = (x, prev[1] + 5.08)
    s.wire(prev, gnd)
    s.gnd(gnd)
    return gnd
