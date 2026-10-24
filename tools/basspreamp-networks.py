#!/usr/bin/env python3
"""Derive the fixed passive/op-amp networks of BassPreamp as analogue
second-order sections, ready to paste into src/basspreamp.dsp.

Usage: python3 tools/basspreamp-networks.py

Component values are those of the public DIY trace cited in
docs/basspreamp/circuit-notes.md. Each network is solved by nodal analysis
with polynomial entries in s (Cramer's rule), so no symbolic package is
needed. Op-amps are ideal: a unity-gain follower's output is a voltage
source equal to its + input, and its input draws no current.

For each network the script prints the poles/zeros, the response at a few
frequencies, and Faust code made of pk.tf2a / pk.tf1a sections (src/lib/pedalkit.lib). Only numpy
is required.
"""

import numpy as np

P = np.polynomial.polynomial          # coefficient order: ascending powers of s


def Y(kind, v):
    """Admittance polynomial of an R or C."""
    return np.array([1 / v]) if kind == "R" else np.array([0.0, v])


def det(m):
    """Determinant of a square matrix of polynomials (Laplace expansion)."""
    n = len(m)
    if n == 1:
        return m[0][0]
    out = np.array([0.0])
    for j in range(n):
        minor = [row[:j] + row[j + 1:] for row in m[1:]]
        term = P.polymul(m[0][j], det(minor))
        out = P.polyadd(out, term if j % 2 == 0 else -term)
    return out


def solve(elements, unknowns, out, alias=None):
    """Transfer function V(out)/V(in) as (num, den) polynomials in s.

    elements: (kind, value, node_a, node_b). Node "in" is the source (1 V),
    "0" is AC ground (the circuit's VB). alias maps a follower's output node
    to its + input; no KCL is written for the output node itself.
    """
    alias = alias or {}
    idx = {n: i for i, n in enumerate(unknowns)}
    n = len(unknowns)
    zero = np.array([0.0])
    A = [[zero for _ in range(n)] for _ in range(n)]
    b = [zero for _ in range(n)]
    for kind, v, a, c in elements:
        y = Y(kind, v)
        for here, there in ((a, c), (c, a)):
            if here not in idx:                     # source, ground or follower output
                continue
            i = idx[here]
            A[i][i] = P.polyadd(A[i][i], y)
            there = alias.get(there, there)
            if there == "in":
                b[i] = P.polyadd(b[i], y)
            elif there != "0":
                A[i][idx[there]] = P.polysub(A[i][idx[there]], y)
    k = idx[alias.get(out, out)]
    num_m = [row[:k] + [b[r]] + row[k + 1:] for r, row in enumerate(A)]
    return P.polytrim(det(num_m), 1e-30), P.polytrim(det(A), 1e-30)


def response(num, den, f):
    s = 2j * np.pi * np.asarray(f)
    return P.polyval(s, num) / P.polyval(s, den)


def sections(num, den):
    """Split into first/second-order sections. Returns a list of
    (num_poly, den_poly) with monic denominators (ascending powers)."""
    zs, ps = P.polyroots(num), P.polyroots(den)
    gain = num[-1] / den[-1]

    def pair(roots):
        roots = sorted(roots, key=lambda r: abs(r))
        cplx = [r for r in roots if abs(r.imag) > 1e-9 * max(1, abs(r))]
        real = sorted([r.real for r in roots if abs(r.imag) <= 1e-9 * max(1, abs(r))], key=abs)
        groups = [[r, np.conj(r)] for r in cplx if r.imag > 0]
        while len(real) >= 2:
            groups.append([real.pop(0), real.pop(0)])
        if real:
            groups.append([real.pop(0)])
        return [np.real(P.polyfromroots(g)) for g in groups]

    dg, ng = pair(ps), pair(zs)
    out = []
    for i, d in enumerate(dg):
        nn = ng[i] if i < len(ng) else np.array([1.0])
        out.append([nn, d])
    # Put the overall high-frequency gain into the first section, then fix the
    # sections so the cascade's DC (or mid-band) level is exact.
    out[0][0] = out[0][0] * gain
    return out


def faust(name, secs):
    lines = [f"{name} = "]
    terms = []
    for nn, d in secs:
        w = np.sqrt(abs(d[0])) if len(d) == 3 else abs(d[0])   # prewarp at the pole frequency
        w = min(w, 2 * np.pi * 15000)
        if len(d) == 3:
            b = np.zeros(3)
            b[:len(nn)] = nn
            terms.append(f"pk.tf2a({b[2]:.10g}, {b[1]:.10g}, {b[0]:.10g}, "
                         f"{d[1]:.10g}, {d[0]:.10g}, {w:.10g})")
        else:
            b = np.zeros(2)
            b[:len(nn)] = nn
            terms.append(f"pk.tf1a({b[1]:.10g}, {b[0]:.10g}, {d[0]:.10g}, {w:.10g})")
    return lines[0] + "\n    : ".join(terms) + ";"


def report(name, num, den, freqs=(20, 41, 80, 110, 200, 420, 1000, 2000, 3300, 5000, 10000)):
    print(f"--- {name}")
    print("  poles (Hz):", ", ".join(f"{abs(p) / 2 / np.pi:.1f}"
                                     + (f" (Q {abs(p) / (-2 * p.real):.2f})" if abs(p.imag) > 1e-6 else "")
                                     for p in P.polyroots(den) if abs(p.imag) >= 0 and p.imag >= -1e-6))
    zs = P.polyroots(num) if len(num) > 1 else []
    print("  zeros (Hz):", ", ".join(f"{abs(z) / 2 / np.pi:.1f}" for z in zs if z.imag >= -1e-6) or "none")
    h = response(num, den, freqs)
    print("  |H| dB:", "  ".join(f"{f}:{20 * np.log10(abs(v)):+.1f}" for f, v in zip(freqs, h)))
    print(faust(name, sections(num, den)))
    print()


# Pre-drive network: R3 bridged by C2-C4-C3 to VB via R4/R5, then C5 into
# IC2_C's + input with R6 to VB. Driven by the input buffer (IC1_D).
pre = solve([("R", 100e3, "in", "B"), ("C", 22e-9, "in", "BL"), ("C", 22e-9, "B", "BR"),
             ("C", 22e-9, "BL", "BR"), ("R", 2.2e3, "BL", "0"), ("R", 22e3, "BR", "0"),
             ("C", 22e-9, "B", "D"), ("R", 100e3, "D", "0")],
            ["B", "BL", "BR", "D"], "D")
report("preNet", *pre)

# Post-clip divider and first Sallen-Key low-pass (IC2_A follower), with the
# R14 + C10 shelf leg at the middle node.
sk1 = solve([("R", 10e3, "in", "P"), ("R", 22e3, "P", "0"), ("R", 22e3, "P", "Q"),
             ("R", 10e3, "Q", "T"), ("C", 47e-9, "T", "0"), ("C", 10e-9, "Q", "O"),
             ("R", 22e3, "Q", "S"), ("C", 470e-12, "S", "0")],
            ["P", "Q", "T", "S"], "O", alias={"O": "S"})
report("postSK1", *sk1)

# Second Sallen-Key low-pass (IC2_B follower).
sk2 = solve([("R", 33e3, "in", "M"), ("C", 2.2e-9, "M", "O"), ("R", 33e3, "M", "N"),
             ("C", 1.2e-9, "N", "0")],
            ["M", "N"], "O", alias={"O": "N"})
report("postSK2", *sk2)

# Bridged-T notch into IC1_A (follower).
bt = solve([("R", 22e3, "in", "W"), ("C", 22e-9, "in", "J"), ("C", 47e-9, "W", "J"),
            ("R", 6.2e3, "J", "0")],
           ["W", "J"], "W")
report("postNotch", *bt)

# Whole post-clip chain, for the notes.
num = P.polymul(P.polymul(sk1[0], sk2[0]), bt[0])
den = P.polymul(P.polymul(sk1[1], sk2[1]), bt[1])
f = np.geomspace(20, 20000, 2000)
h = 20 * np.log10(abs(response(num, den, f)))
print("--- post chain: peak {:+.1f} dB at {:.0f} Hz, -3 dB re 100 Hz at {:.0f} Hz, "
      "min {:+.1f} dB at {:.0f} Hz".format(h.max(), f[h.argmax()],
                                         f[np.argmax((f > 1000) & (h < h[np.searchsorted(f, 100)] - 3))],
                                         h[f < 2000].min(), f[f < 2000][h[f < 2000].argmin()]))
hp = 20 * np.log10(abs(response(*pre, f)))
print("--- pre net: max {:+.1f} dB at {:.0f} Hz, min {:+.1f} dB at {:.0f} Hz".format(
    hp.max(), f[hp.argmax()], hp[f > 50].min(), f[f > 50][hp[f > 50].argmin()]))
