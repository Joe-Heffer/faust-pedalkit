# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Write KiCad schematics (.kicad_sch, .kicad_pro) from a Python description.

Each effect's schematic is described by a script, tools/schematics/<name>.py,
which builds a Project with this module. tools/schematics/build.py runs the
script and writes docs/<name>/schematics/. The scripts are the source: never
edit the generated .kicad_sch by hand. See docs/development/schematics.md.

What the module takes care of, so the scripts only say what goes where:

- The conventions in docs/development/schematics.md: Reference, Value,
  Confidence and Source shown on every part, a dashed outline round every
  inferred or chosen part, the title block, sheet names and file names.
- Symbol definitions, copied from the stock KiCad libraries installed on the
  machine (KICAD_SYMBOL_DIR, default /usr/share/kicad/symbols), so the copies
  embedded in each sheet match the library exactly.
- Pin positions, from those definitions, so wires can be drawn pin to pin.
- Junctions, wherever three or more connections meet.
- Deterministic UUIDs (uuid5), so regenerating an unchanged script gives
  byte-identical files and `build.py --check` can spot a stale schematic.

Units are millimetres. Keep every coordinate on the 1.27 mm (50 mil) grid,
which is what KiCad's editor snaps to and what pin ends sit on.
"""

import math
import os
import re
import uuid
from pathlib import Path

# KiCad 8 schematic format, the oldest version that issue #11 asks the files
# to open in. Newer KiCad versions read it unchanged.
SCH_VERSION = "20231120"
GENERATOR_VERSION = "8.0"

CONFIDENCE = ("documented", "reported", "inferred", "chosen")
SOURCE_RE = re.compile(r"^(-|\[\d+\](, \[\d+\])*)$")

FONT = 1.27  # text size of fields and labels
LINE = 2.54  # spacing of stacked fields
CHAR_W = 1.05  # rough advance of one character at FONT, for outlines
UUID_NS = uuid.UUID("5d0f6f8e-6a43-4c38-9a8b-6a2f1f7c2a10")  # pedalkit schematics

# Paper and the title block's corner, for layout checks (A4 landscape).
PAPER = (297.0, 210.0)
TITLE_BLOCK_TOP_LEFT = (175.26, 175.26)


# ---------------------------------------------------------------------------
# Values
# ---------------------------------------------------------------------------

_PREFIX = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "m": 1e-3, "k": 1e3, "M": 1e6, "G": 1e9}


def val(text):
    """Number at the start of a component value: "3.3k" -> 3300.0,
    "33n" -> 3.3e-8, "4k7" -> 4700.0, "1M log" -> 1e6, "2.6H" -> 2.6."""
    m = re.match(r"^\s*(\d+(?:\.\d+)?)([pnuµmkMG]?)(\d*)", text)
    if not m:
        raise ValueError(f"no value in {text!r}")
    num, pre, frac = m.groups()
    x = float(f"{num}.{frac}") if frac and "." not in num else float(num)
    return x * _PREFIX.get(pre, 1.0)


def rc_hz(r, c):
    """Corner frequency of an RC pair, 1 / (2 pi R C); strings go through val()."""
    r, c = (val(v) if isinstance(v, str) else v for v in (r, c))
    return 1 / (2 * math.pi * r * c)


def lc_hz(l_, c):
    """Resonance of an LC pair, 1 / (2 pi sqrt(L C))."""
    l_, c = (val(v) if isinstance(v, str) else v for v in (l_, c))
    return 1 / (2 * math.pi * math.sqrt(l_ * c))


def expect(what, actual, target, rel=0.05):
    """Fail generation unless actual is within rel of target. Each effect
    script uses this to check its component values against the circuit notes
    and the DSP constants, so the drawing can't drift from them silently."""
    if not math.isclose(actual, target, rel_tol=rel):
        raise AssertionError(f"{what}: {actual:.4g}, expected {target:.4g} (±{rel:.0%})")
    return actual


def hz(f):
    """Frequency as text for the sheet: 1460 -> "1.46 kHz"."""
    if f >= 1000:
        return f"{f / 1000:.3g} kHz"
    return f"{f:.3g} Hz"


# ---------------------------------------------------------------------------
# S-expressions
# ---------------------------------------------------------------------------


class Q(str):
    """A quoted string atom."""


_TOKEN = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))')


def parse(text):
    """Parse KiCad s-expression text into nested lists of str and Q atoms."""
    stack, out = [], []
    pos = 0
    while True:
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            break
        pos = m.end()
        op, cl, qs, atom = m.groups()
        if op:
            stack.append(out)
            out = []
        elif cl:
            done = out
            out = stack.pop()
            out.append(done)
        elif qs is not None:
            out.append(Q(qs.replace('\\"', '"').replace("\\\\", "\\")))
        else:
            out.append(atom)
    return out[0]


def quote(s):
    s = str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{s}"'


def dump(node, indent=0):
    """Serialise a parsed s-expression, one top-level child per line."""
    pad = "  " * indent
    if not isinstance(node, list):
        return quote(node) if isinstance(node, Q) else node
    simple = all(not isinstance(c, list) for c in node) or node[0] in (
        "property",
        "pin",
        "polyline",
        "rectangle",
        "circle",
        "arc",
        "text",
        "pin_names",
        "pin_numbers",
        "effects",
    )
    if simple:
        return "(" + " ".join(_flat(c) for c in node) + ")"
    head = [c for c in node if not isinstance(c, list)]
    kids = [c for c in node if isinstance(c, list)]
    lines = ["(" + " ".join(_flat(c) for c in head)]
    for k in kids:
        lines.append(pad + "  " + dump(k, indent + 1))
    return "\n".join(lines) + ")"


def _flat(node):
    if not isinstance(node, list):
        return quote(node) if isinstance(node, Q) else node
    return "(" + " ".join(_flat(c) for c in node) + ")"


def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def first(node, key):
    found = find(node, key)
    return found[0] if found else None


# ---------------------------------------------------------------------------
# Library symbols
# ---------------------------------------------------------------------------


# Tokens newer libraries add that KiCad 8 does not know.
_NEWER = ("embedded_fonts", "duplicate_pin_numbers_are_jumpers", "jumper_pin_groups", "in_pos_files")
_NEWER_PROP = ("show_name", "do_not_autoplace")


def _kicad8(node):
    """Rewrite a library symbol from a newer KiCad into KiCad 8 syntax, so
    the copies embedded in a sheet open in KiCad 8: `(hide yes)` becomes the
    bare `hide` KiCad 8 expects (inside `effects` for a property), empty pin
    names become "~", and tokens KiCad 8 does not know are dropped."""
    if not isinstance(node, list):
        return node
    head = node[0] if node else None
    hidden = ["hide", "yes"] in node or "hide" in node[1:]
    out = []
    for c in node:
        if isinstance(c, list) and c[:1] == ["hide"]:
            continue
        if c == "hide":
            continue
        if isinstance(c, list) and c and c[0] in _NEWER:
            continue
        if head == "property" and isinstance(c, list) and c and c[0] in _NEWER_PROP:
            continue
        if head == "property" and isinstance(c, list) and c[:1] == ["effects"] and hidden:
            out.append([_kicad8(x) for x in c] + ["hide"])
            continue
        if c == ["power", "global"]:
            c = ["power"]
        if head == "name" and isinstance(c, Q) and c == "":
            c = Q("~")
        out.append(_kicad8(c))
    if hidden and head in ("pin_names", "pin_numbers", "pin", "effects"):
        if head == "pin":
            i = next(i for i, c in enumerate(out) if isinstance(c, list) and c[:1] == ["length"])
            out.insert(i + 1, "hide")
        else:
            out.append("hide")
    return out


class LibSymbol:
    """One symbol from a stock library: its definition and pin geometry."""

    def __init__(self, lib_id, sexpr):
        self.lib_id = lib_id
        self.sexpr = sexpr
        self.pins = {}  # number -> (x, y, angle, length, name, type)
        self.points = []  # body graphics, symbol coordinates (y up)
        self.power = first(sexpr, "power") is not None or "power" in sexpr
        for sub in find(sexpr, "symbol"):
            unit = sub[1].rsplit("_", 2)
            if len(unit) == 3 and (unit[1] not in ("0", "1") or unit[2] not in ("0", "1")):
                continue
            for item in sub[2:]:
                if not isinstance(item, list):
                    continue
                if item[0] == "pin":
                    at = first(item, "at")
                    num = first(item, "number")[1]
                    name = first(item, "name")[1]
                    length = float(first(item, "length")[1])
                    x, y, a = float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0
                    self.pins[str(num)] = (x, y, a, length, str(name), item[1])
                    self.points.append((x, y))
                elif item[0] in ("rectangle",):
                    for k in ("start", "end"):
                        p = first(item, k)
                        self.points.append((float(p[1]), float(p[2])))
                elif item[0] == "polyline":
                    for p in find(first(item, "pts"), "xy"):
                        self.points.append((float(p[1]), float(p[2])))
                elif item[0] == "circle":
                    c, r = first(item, "center"), float(first(item, "radius")[1])
                    cx, cy = float(c[1]), float(c[2])
                    self.points += [(cx - r, cy - r), (cx + r, cy + r)]
                elif item[0] == "arc":
                    for k in ("start", "mid", "end"):
                        p = first(item, k)
                        self.points.append((float(p[1]), float(p[2])))

    def embedded(self):
        """The definition as embedded in a schematic's lib_symbols."""
        node = list(self.sexpr)
        node[1] = Q(self.lib_id)
        return _kicad8(node)


class Library:
    """Stock KiCad symbol libraries, read on demand."""

    def __init__(self, root=None):
        self.root = Path(root or os.environ.get("KICAD_SYMBOL_DIR", "/usr/share/kicad/symbols"))
        self._libs = {}
        self._syms = {}

    def _lib(self, name):
        if name not in self._libs:
            path = self.root / f"{name}.kicad_sym"
            if not path.exists():
                raise FileNotFoundError(
                    f"{path} not found. Install the stock KiCad symbol libraries "
                    "(Arch: kicad-library) or set KICAD_SYMBOL_DIR, or run in the docs image."
                )
            tree = parse(path.read_text(encoding="utf-8"))
            self._libs[name] = {str(s[1]): s for s in find(tree, "symbol")}
        return self._libs[name]

    def get(self, lib_id):
        if lib_id in self._syms:
            return self._syms[lib_id]
        libname, name = lib_id.split(":", 1)
        lib = self._lib(libname)
        node = lib[name]
        ext = first(node, "extends")
        if ext:
            # Flatten an alias: the parent's graphics and pins, this symbol's
            # properties, with the sub-symbol units renamed after this symbol.
            parent = lib[str(ext[1])]
            props = {str(p[1]): p for p in find(node, "property")}
            flat = [node[0], node[1]]
            for c in parent[2:]:
                if isinstance(c, list) and c[0] == "property" and str(c[1]) in props:
                    flat.append(props.pop(str(c[1])))
                elif isinstance(c, list) and c[0] == "symbol":
                    sub = list(c)
                    sub[1] = Q(name + str(c[1])[len(str(ext[1])) :])
                    flat.append(sub)
                else:
                    flat.append(c)
            flat[2:2] = list(props.values())
            node = flat
        sym = LibSymbol(lib_id, node)
        self._syms[lib_id] = sym
        return sym


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


def _rot(x, y, angle):
    """Rotate a symbol-space point counter-clockwise by a multiple of 90°."""
    a = int(angle) % 360
    return {0: (x, y), 90: (-y, x), 180: (-x, -y), 270: (y, -x)}[a]


def _r(v):
    return round(v + 0.0, 2)


def _fmt(v):
    v = _r(v)
    return f"{v:g}" if v != int(v) else str(int(v))


def P(x, y):
    """A point, rounded to the 0.01 mm KiCad stores."""
    return (_r(x), _r(y))


# ---------------------------------------------------------------------------
# Schematic items
# ---------------------------------------------------------------------------


class Part:
    """A placed symbol. part["1"] is the absolute position of pin 1."""

    def __init__(self, sheet, sym, ref, value, confidence, source, at, rot, fields, extra, mirror=None):
        self.sheet, self.sym, self.ref, self.value = sheet, sym, ref, value
        self.mirror = mirror
        self.confidence, self.source = confidence, source
        self.at, self.rot, self.fields, self.extra = P(*at), rot, fields, extra
        self.uuid = sheet.uid(f"sym:{ref}")

    def __getitem__(self, pin):
        x, y, *_ = self._pin(pin)
        dx, dy = _rot(*self._mirror(x, y), self.rot)
        return P(self.at[0] + dx, self.at[1] - dy)

    def _pin(self, pin):
        pin = str(pin)
        if pin in self.sym.pins:
            return self.sym.pins[pin]
        named = [p for p in self.sym.pins.values() if p[4] == pin]
        if len(named) == 1:
            return named[0]
        raise KeyError(f"{self.ref}: no pin {pin!r} in {self.sym.lib_id}")

    def _mirror(self, x, y):
        # KiCad mirrors in symbol space, before rotating: "x" flips the symbol
        # top to bottom, "y" left to right.
        if self.mirror == "x":
            return x, -y
        if self.mirror == "y":
            return -x, y
        return x, y

    def body_box(self):
        pts = [_rot(*self._mirror(x, y), self.rot) for x, y in self.sym.points]
        xs = [self.at[0] + x for x, _ in pts]
        ys = [self.at[1] - y for _, y in pts]
        return min(xs), min(ys), max(xs), max(ys)

    def field_lines(self):
        lines = [("Reference", self.ref), ("Value", self.value)]
        if not self.sym.power:
            lines += [("Confidence", self.confidence), ("Source", self.source)]
        return lines

    def field_layout(self):
        """(name, text, x, y, justify) for each shown field."""
        x0, y0, x1, y1 = self.body_box()
        lines = self.field_lines()
        n = len(lines)
        side = self.fields
        out = []
        if side in ("right", "left"):
            top = (y0 + y1) / 2 - (n - 1) * LINE / 2
            x = x1 + 1.27 if side == "right" else x0 - 1.27
            just = "left" if side == "right" else "right"
            for i, (k, t) in enumerate(lines):
                out.append((k, t, x, top + i * LINE, just))
        elif side == "upright":
            # Right of the body and above its centre line, clear of an
            # op-amp's output wire.
            bottom = (y0 + y1) / 2 - LINE
            for i, (k, t) in enumerate(lines):
                out.append((k, t, x1 + 1.27, bottom - (n - 1 - i) * LINE, "left"))
        elif side in ("above", "below"):
            cx = (x0 + x1) / 2
            top = y0 - 1.27 - (n - 0.5) * LINE if side == "above" else y1 + 1.27 + LINE / 2
            for i, (k, t) in enumerate(lines):
                out.append((k, t, cx, top + i * LINE, None))
        else:
            raise ValueError(f"{self.ref}: fields must be right, upright, left, above or below")
        return [(k, t, _r(x), _r(y), j) for k, t, x, y, j in out]

    def outline_box(self):
        """Box round the body and its fields, for the dashed outline."""
        x0, y0, x1, y1 = self.body_box()
        for _, t, x, y, j in self.field_layout():
            w = len(t) * CHAR_W
            if j == "left":
                fx0, fx1 = x, x + w
            elif j == "right":
                fx0, fx1 = x - w, x
            else:
                fx0, fx1 = x - w / 2, x + w / 2
            x0, x1 = min(x0, fx0), max(x1, fx1)
            y0, y1 = min(y0, y - FONT / 2 - 0.3), max(y1, y + FONT / 2 + 0.3)
        m = 0.8
        return x0 - m, y0 - m, x1 + m, y1 + m

    def sexpr(self, project):
        hide_ref = self.sym.power
        props = []
        for k, t, x, y, j in self.field_layout():
            if self.rot % 360 in (90, 180):
                # The field ends up drawn at 180°, which KiCad turns round to
                # keep it readable, swapping left and right justification.
                j = {"left": "right", "right": "left"}.get(j, j)
            just = f" (justify {j})" if j else ""
            hide = " hide" if (hide_ref and k == "Reference") else ""
            # A field's angle is relative to the symbol, so undo the
            # symbol's rotation to keep every field horizontal.
            props.append(
                f"(property {quote(k)} {quote(t)} (at {_fmt(x)} {_fmt(y)} {self.rot % 180}) "
                f"(effects (font (size {FONT} {FONT})){just}{hide}))"
            )
        if hide_ref:
            # Power symbols show only their net name, under or over the symbol.
            props = [
                f"(property \"Reference\" {quote(self.ref)} (at {_fmt(self.at[0])} {_fmt(self.at[1])} 0) "
                f"(effects (font (size {FONT} {FONT})) hide))",
                self._power_value(),
            ]
        for k in ("Footprint", "Datasheet", "Description"):
            props.append(
                f"(property {quote(k)} \"\" (at {_fmt(self.at[0])} {_fmt(self.at[1])} 0) "
                f"(effects (font (size {FONT} {FONT})) hide))"
            )
        pins = " ".join(f"(pin {quote(n)} (uuid {quote(self.sheet.uid(f'pin:{self.ref}:{n}'))}))" for n in self.sym.pins)
        inst = (
            f"(instances (project {quote(project.name)} (path {quote(self.sheet.path)} "
            f"(reference {quote(self.ref)}) (unit 1))))"
        )
        return (
            f"(symbol (lib_id {quote(self.sym.lib_id)}) (at {_fmt(self.at[0])} {_fmt(self.at[1])} {self.rot}) "
            + (f"(mirror {self.mirror}) " if self.mirror else "")
            + f"(unit 1) (exclude_from_sim no) (in_bom {'no' if self.sym.power else 'yes'}) "
            f"(on_board {'no' if self.sym.power else 'yes'}) (dnp no) (uuid {quote(self.uuid)}) "
            + " ".join(props)
            + f" {pins} {inst})"
        )

    def _power_value(self):
        x0, y0, x1, y1 = self.body_box()
        up = self.extra.get("up", True)
        y = y0 - 1.27 if up else y1 + 1.27
        if self.rot in (90, 270):
            y = (y0 + y1) / 2
        return (
            f"(property \"Value\" {quote(self.value)} (at {_fmt(self.at[0])} {_fmt(y)} {self.rot % 180}) "
            f"(effects (font (size {FONT} {FONT}))))"
        )


class Sheet:
    """One .kicad_sch file: the root sheet or a stage's sub-sheet."""

    def __init__(self, project, number, title, file, pins=()):
        self.project, self.number, self.title, self.file = project, number, title, file
        self.pins = list(pins)  # (name, shape) for a sub-sheet's hierarchical labels
        self.parts, self.wires, self.items, self.boxes = [], [], [], []
        self.points = []  # connection points of labels and power symbols
        self._n = 0
        self.uuid = project.uid(f"sheet:{file}")
        self.path = None  # set by Project when the sheet is placed
        self.page = None

    @property
    def name(self):
        return f"{self.number} {self.title}" if self.number is not None else self.title

    def uid(self, key=None):
        if key is None:
            self._n += 1
            key = f"#{self._n}"
        return str(uuid.uuid5(UUID_NS, f"{self.project.name}/{self.file}/{key}"))

    # -- parts ------------------------------------------------------------

    def part(self, lib_id, ref, value, confidence, source, at, rot=0, fields="right", mirror=None):
        """Place a component. confidence: documented/reported/inferred/chosen;
        source: "[n]" (or "[n], [m]") from the notes' source list, or "-"."""
        if confidence not in CONFIDENCE:
            raise ValueError(f"{ref}: confidence {confidence!r} not one of {CONFIDENCE}")
        if not SOURCE_RE.match(source):
            raise ValueError(f"{ref}: source {source!r} must be like [2] or -")
        self.project.claim(ref)
        p = Part(self, self.project.lib.get(lib_id), ref, value, confidence, source, at, rot, fields, {}, mirror)
        self.parts.append(p)
        if confidence in ("inferred", "chosen"):
            self.boxes.append(p)
        return p

    def _power(self, lib_id, at, rot=0, up=True):
        sym = self.project.lib.get(lib_id)
        prefix = "#FLG" if "FLAG" in lib_id else "#PWR"
        ref = self.project.next_power(prefix)
        p = Part(self, sym, ref, _prop(sym, "Value"), "chosen", "-", at, rot, "right", {"up": up})
        self.parts.append(p)
        return p

    def gnd(self, at):
        """Ground symbol whose pin sits at `at`."""
        return self._power("power:GND", at, up=False)

    def supply(self, at, net="+9V"):
        """Supply symbol (e.g. +9V) whose pin sits at `at`."""
        return self._power(f"power:{net}", at)

    def pwr_flag(self, at, up=True):
        """PWR_FLAG, telling ERC that the net at `at` is driven."""
        return self._power("power:PWR_FLAG", at, rot=0 if up else 180, up=up)

    # -- wires and labels ------------------------------------------------

    def wire(self, *pts, vfirst=False):
        """Wire through the points; a diagonal step becomes an L, horizontal
        first unless vfirst."""
        pts = [P(*p) for p in pts]
        for a, b in zip(pts, pts[1:], strict=False):
            if a[0] != b[0] and a[1] != b[1]:
                c = (a[0], b[1]) if vfirst else (b[0], a[1])
                self._seg(a, c)
                self._seg(c, b)
            else:
                self._seg(a, b)

    def _seg(self, a, b):
        if a != b:
            self.wires.append((a, b))

    def glabel(self, name, at, angle=0, shape="input"):
        """Global label (e.g. the bias rail VB). angle: the side the label's
        text extends to, 0 right, 180 left, 90 up, 270 down."""
        at = P(*at)
        self.points.append(at)
        just = "left" if angle in (0, 90) else "right"
        self.items.append(
            f"(global_label {quote(name)} (shape {shape}) (at {_fmt(at[0])} {_fmt(at[1])} {angle}) "
            f"(fields_autoplaced yes) (effects (font (size {FONT} {FONT})) (justify {just})) "
            f"(uuid {quote(self.uid())}) (property \"Intersheetrefs\" \"${{INTERSHEET_REFS}}\" "
            f"(at {_fmt(at[0])} {_fmt(at[1])} 0) (effects (font (size {FONT} {FONT})) hide)))"
        )

    def hlabel(self, name, at, angle=0):
        """Hierarchical label for one of the sheet's pins (declared in pins=)."""
        shapes = dict(self.pins)
        if name not in shapes:
            raise KeyError(f"{self.file}: {name} is not one of the sheet's pins {list(shapes)}")
        at = P(*at)
        self.points.append(at)
        just = "left" if angle in (0, 90) else "right"
        self.items.append(
            f"(hierarchical_label {quote(name)} (shape {shapes[name]}) (at {_fmt(at[0])} {_fmt(at[1])} {angle}) "
            f"(effects (font (size {FONT} {FONT})) (justify {just})) (uuid {quote(self.uid())}))"
        )

    def text(self, body, at, size=FONT, bold=False):
        """Free text: a stage title, a corner frequency, a note."""
        if isinstance(body, (list, tuple)):
            body = "\n".join(body)
        at = P(*at)
        b = " bold" if bold else ""
        self.items.append(
            f"(text {quote(body)} (exclude_from_sim no) (at {_fmt(at[0])} {_fmt(at[1])} 0) "
            f"(effects (font (size {size} {size}){b}) (justify left bottom)) (uuid {quote(self.uid())}))"
        )

    def heading(self, body):
        """The stage title, top left."""
        self.text(body, (25.4, 30.48), size=2.54)

    def note(self, lines):
        """The sheet's explanatory note, bottom left beside the title block:
        what was inferred or chosen and why, one line per part or group."""
        for line in lines:
            if len(line) * CHAR_W > TITLE_BLOCK_TOP_LEFT[0] - 30:
                raise AssertionError(f"{self.file}: note line runs into the title block: {line!r}")
        self.text(lines, (25.4, 198.12))

    def opamp_power(self, u, supply="+9V"):
        """Tie an op-amp's V+ pin to the supply and V- to ground."""
        self.supply(u["3"], supply)
        self.gnd(u["4"])

    # -- output ----------------------------------------------------------

    def _junctions(self):
        ends = {}
        for a, b in self.wires:
            for p in (a, b):
                ends[p] = ends.get(p, 0) + 1
        for part in self.parts:
            for n in part.sym.pins:
                p = part[n]
                ends[p] = ends.get(p, 0) + 1
        for p in self.points:
            ends[p] = ends.get(p, 0) + 1
        out = []
        for p, n in ends.items():
            n += 2 * sum(1 for a, b in self.wires if _inside(p, a, b))
            if n >= 3:
                out.append(p)
        return sorted(out)

    def check(self):
        """Layout checks: everything on the page, clear of the title block,
        and no pin left dangling."""
        tb = TITLE_BLOCK_TOP_LEFT
        for part in self.parts:
            x0, y0, x1, y1 = part.outline_box()
            if x0 < 10 or y0 < 10 or x1 > PAPER[0] - 10 or y1 > PAPER[1] - 10:
                raise AssertionError(f"{self.file}: {part.ref} runs off the page")
            if x1 > tb[0] and y1 > tb[1]:
                raise AssertionError(f"{self.file}: {part.ref} overlaps the title block")
        nodes = set()
        for a, b in self.wires:
            nodes.update((a, b))
        nodes.update(self.points)
        allpins = {}
        for part in self.parts:
            for n in part.sym.pins:
                allpins.setdefault(part[n], []).append((part.ref, n))
        for part in self.parts:
            for n in part.sym.pins:
                p = part[n]
                on_wire = p in nodes or any(_inside(p, a, b) for a, b in self.wires)
                if not on_wire and len(allpins[p]) < 2:
                    raise AssertionError(f"{self.file}: pin {n} of {part.ref} at {p} is not connected")
        for a, b in self.wires:
            for p in (a, b):
                hits = p in allpins or p in self.points
                hits = hits or sum(1 for w in self.wires for q in w if q == p) > 1
                hits = hits or any(_inside(p, c, d) for c, d in self.wires)
                if not hits:
                    raise AssertionError(f"{self.file}: wire end {p} is not connected to anything")

    def render(self):
        self.check()
        p = self.project
        syms = sorted({part.sym.lib_id: part.sym for part in self.parts}.values(), key=lambda s: s.lib_id)
        out = [
            "(kicad_sch",
            f"  (version {SCH_VERSION})",
            '  (generator "eeschema")',
            f'  (generator_version "{GENERATOR_VERSION}")',
            f"  (uuid {quote(self.uuid)})",
            '  (paper "A4")',
            "  (title_block",
            f"    (title {quote(p.title if self.number is None else f'{p.title}: {self.name}')})",
            f"    (date {quote(p.date)})",
            f"    (rev {quote(p.rev)})",
            '    (company "Redrawn from public sources; see circuit notes")',
            '    (comment 1 "Licence: CC-BY-4.0")',
            f"    (comment 2 {quote(p.hardware)})",
            '    (comment 3 "Dashed outline: inferred or chosen part (Confidence and Source fields under each part)")',
            f"    (comment 4 {quote(p.caveat)})",
            "  )",
            "  (lib_symbols",
        ]
        for s in syms:
            out.append("    " + dump(s.embedded(), 2))
        out.append("  )")
        for j in self._junctions():
            out.append(
                f"  (junction (at {_fmt(j[0])} {_fmt(j[1])}) (diameter 0) (color 0 0 0 0) "
                f"(uuid {quote(self.uid(f'junction:{j}'))}))"
            )
        for a, b in self.wires:
            out.append(
                f"  (wire (pts (xy {_fmt(a[0])} {_fmt(a[1])}) (xy {_fmt(b[0])} {_fmt(b[1])})) "
                f"(stroke (width 0) (type default)) (uuid {quote(self.uid(f'wire:{a}:{b}'))}))"
            )
        for part in self.boxes:
            x0, y0, x1, y1 = part.outline_box()
            out.append(
                f"  (rectangle (start {_fmt(x0)} {_fmt(y0)}) (end {_fmt(x1)} {_fmt(y1)}) "
                f"(stroke (width 0) (type dash) (color 0 0 194 1)) (fill (type none)) (uuid {quote(self.uid(f'outline:{part.ref}'))}))"
            )
        for item in self.items:
            out.append("  " + item)
        for part in self.parts:
            out.append("  " + part.sexpr(p))
        for blk in getattr(self, "blocks", []):
            out.append("  " + blk.sexpr())
        if self.number is None:
            out.append('  (sheet_instances (path "/" (page "1")))')
        out.append(")")
        return "\n".join(out) + "\n"


def _inside(p, a, b):
    """True if p lies strictly inside the segment a-b."""
    if a[0] == b[0] == p[0]:
        return min(a[1], b[1]) < p[1] < max(a[1], b[1])
    if a[1] == b[1] == p[1]:
        return min(a[0], b[0]) < p[0] < max(a[0], b[0])
    return False


def _prop(sym, key):
    for pr in find(sym.sexpr, "property"):
        if str(pr[1]) == key:
            return str(pr[2])
    return ""


class Block:
    """A hierarchical sheet placed on the root sheet, with its pins."""

    def __init__(self, root, sheet, at, size):
        self.root, self.sheet = root, sheet
        self.at, self.size = P(*at), P(*size)
        ins = [n for n, s in sheet.pins if s == "input"]
        outs = [n for n, s in sheet.pins if s != "input"]
        self.pin_at = {}
        x, y = self.at
        w, h = self.size
        for side, names in ((x, ins), (x + w, outs)):
            for i, n in enumerate(names):
                self.pin_at[n] = P(side, y + 5.08 + i * 5.08)
        if max(len(ins), len(outs)) * 5.08 + 2.54 > h:
            raise AssertionError(f"block {sheet.name} too short for its pins")
        root.points.extend(self.pin_at.values())

    def __getitem__(self, name):
        return self.pin_at[name]

    def sexpr(self):
        s, root = self.sheet, self.root
        x, y = self.at
        w, h = self.size
        pins = []
        for n, shape in s.pins:
            px, py = self.pin_at[n]
            ang, just = (180, "left") if px == x else (0, "right")
            pins.append(
                f"(pin {quote(n)} {shape} (at {_fmt(px)} {_fmt(py)} {ang}) "
                f"(effects (font (size {FONT} {FONT})) (justify {just})) (uuid {quote(root.uid(f'blockpin:{s.file}:{n}'))}))"
            )
        return (
            f"(sheet (at {_fmt(x)} {_fmt(y)}) (size {_fmt(w)} {_fmt(h)}) (fields_autoplaced yes) "
            f"(stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000)) (uuid {quote(s.uuid)}) "
            f"(property \"Sheetname\" {quote(s.name)} (at {_fmt(x)} {_fmt(y - 0.71)} 0) "
            f"(effects (font (size {FONT} {FONT})) (justify left bottom))) "
            f"(property \"Sheetfile\" {quote(s.file)} (at {_fmt(x)} {_fmt(y + h + 0.71)} 0) "
            f"(effects (font (size {FONT} {FONT})) (justify left top))) "
            + " ".join(pins)
            + f" (instances (project {quote(root.project.name)} (path {quote(root.path)} (page {quote(str(s.page))})))))"
        )


class Project:
    """A root sheet plus one sub-sheet per stage, written as a KiCad project."""

    def __init__(self, name, title, hardware, date, rev="0.1", caveat="", library=None):
        self.name, self.title, self.date, self.rev = name, title, date, rev
        self.hardware = f"Reference hardware, named for identification only: {hardware}"
        self.caveat = caveat
        for line in (self.hardware, caveat):
            if len(line) > 88:
                raise ValueError(f"title block comment too long for the title block: {line!r}")
        self.lib = library or Library()
        self._refs = set()
        self._power_n = {}
        self.root = Sheet(self, None, title, f"{name}.kicad_sch")
        self.root.path = f"/{self.root.uuid}"
        self.root.blocks = []
        self.sheets = []

    def uid(self, key):
        return str(uuid.uuid5(UUID_NS, f"{self.name}/{key}"))

    def claim(self, ref):
        if ref in self._refs:
            raise ValueError(f"designator {ref} used twice")
        self._refs.add(ref)

    def next_power(self, prefix):
        self._power_n[prefix] = self._power_n.get(prefix, 0) + 1
        return f"{prefix}{self._power_n[prefix]:02d}"

    def sheet(self, number, title, pins=()):
        """A stage's sub-sheet, named and numbered like its circuit-notes section."""
        slug = re.sub(r"[^a-z0-9]+", "-", f"{number} {title}".lower()).strip("-")
        s = Sheet(self, number, title, f"{slug}.kicad_sch", pins)
        s.path = f"{self.root.path}/{s.uuid}"
        s.page = len(self.sheets) + 2
        self.sheets.append(s)
        return s

    def block(self, sheet, at, size=(38.1, 20.32)):
        """Place a sub-sheet on the root sheet; block["IN"] is its pin."""
        b = Block(self.root, sheet, at, size)
        self.root.blocks.append(b)
        return b

    def files(self):
        """{file name: text} for the project, root sheet and sub-sheets."""
        placed = {b.sheet.file for b in self.root.blocks}
        for s in self.sheets:
            if s.file not in placed:
                raise AssertionError(f"sheet {s.name} is not placed on the root sheet")
        out = {self.root.file: self.root.render()}
        for s in self.sheets:
            out[s.file] = s.render()
        sheets = ",\n".join(
            f'    [\n      "{s.uuid}",\n      {quote(n)}\n    ]'
            for s, n in [(self.root, "Root")] + [(s, s.name) for s in self.sheets]
        )
        out[f"{self.name}.kicad_pro"] = (
            "{\n"
            '  "meta": {\n'
            f'    "filename": "{self.name}.kicad_pro",\n'
            '    "version": 1\n'
            "  },\n"
            '  "schematic": {\n'
            '    "legacy_lib_dir": "",\n'
            '    "legacy_lib_list": []\n'
            "  },\n"
            '  "sheets": [\n'
            f"{sheets}\n"
            "  ],\n"
            '  "text_variables": {}\n'
            "}\n"
        )
        return out
