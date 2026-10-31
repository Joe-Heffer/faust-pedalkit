#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Fail if an effect is missing anything the new-effect checklist requires.

Usage: check-effects.py [--root DIR] [NAME...]
       check-effects.py --dsp-only FILE...

For every src/<name>.dsp (or only the NAMEs given), checks the parts of the
checklist in AGENTS.md ("Adding a new effect") that can be checked without
compiling anything:

* the DSP: the required `declare`s, a `major.minor.micro` version, a unit and
  si.smoo smoothing on every control, a Latency bargraph tagged
  [lv2:reportsLatency] whenever it uses pk.oversample4, and pk.safety on the
  output
* the notes: docs/<name>/design-notes.md or circuit-notes.md, with the
  sections their outlines require (prior art, measurable targets and open
  questions in design notes; sources and open questions in circuit notes)
* the docs: docs/<name>/index.md, docs/<name>/changelog.md with a section for
  the declared version, rows in README.md, docs/index.md and
  docs/effects/index.md, and the pages in the mkdocs.yml nav
* the effect page: the sections every page has (Download, Controls, Signal
  path, Measured behaviour, What to tune by ear, Known limitations, and
  Presets when there are presets), every control and every preset named, and
  a link to the CSV data under every embedded measurement plot
* the schematic: when there are circuit notes, the root sheet embedded on the
  effect page and every sub-sheet named in the root schematic embedded in
  the effect's docs
* the tests: tests/<name>/ with the minimum set (test_silence.py,
  test_peak.py, test_freqresp.py, test_harmonics.py), an aliasing comparison
  against RENDER_1X when the effect oversamples, test_presets.py when it has
  presets, and a finish() call in every script

With --dsp-only, only the DSP checks run, on the given .dsp files wherever
they are. The effect designer's generated examples (tests/web/designer/) use
this: a downloaded design has no notes, docs or tests yet.

Whether the effect compiles, passes its tests and has a schematic is checked
elsewhere (faust-compile, make test, schematics-present), and whether the
plots, schematics and plugins the docs rely on are generated is checked by
tools/check-outputs.py once they are built. Used by the effect-checklist
pre-commit hook.
"""

import argparse
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DECLARES = ("name", "description", "author", "license", "version", "lv2class")
MINIMUM_TESTS = ("test_silence.py", "test_peak.py", "test_freqresp.py", "test_harmonics.py")
# Sections every effect page has, as `## ` headings (docs/bassdrive/index.md).
PAGE_SECTIONS = (
    "Download",
    "Controls",
    "Signal path",
    "Measured behaviour",
    "What to tune by ear",
    "Known limitations",
)
# Sections the outlines in AGENTS.md require, matched at the start of a
# `## ` heading after any section number.
NOTES_SECTIONS = {
    "design-notes.md": ("Prior art", "Measurable targets", "Open questions"),
    "circuit-notes.md": ("Sources", "Open questions"),
}
# Controls that need a unit; checkboxes and buttons are unitless switches.
RANGED_CONTROLS = ("hslider", "vslider", "nentry")
SMOOTHED_CONTROLS = (*RANGED_CONTROLS, "checkbox")


def strip_comments(src):
    """Remove // and /* */ comments from Faust source, leaving strings intact."""
    out = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == '"':
            j = src.find('"', i + 1)
            j = n if j < 0 else j + 1
            out.append(src[i:j])
            i = j
        elif src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def declares(code):
    return dict(re.findall(r'^\s*declare\s+(\w+)\s+"([^"]*)"\s*;', code, re.M))


def control_labels(code):
    """The label of every control and bargraph, without [metadata] or [n]."""
    out = []
    pattern = r"\b(?:" + "|".join((*SMOOTHED_CONTROLS, "button")) + r')\s*\(\s*"([^"]*)"'
    for label in re.findall(pattern, code):
        name = re.sub(r"\[[^]]*\]", "", label).strip()
        if name and name not in out:
            out.append(name)
    return out


def headings(text, level=2):
    """`## ` headings, with any leading section number removed."""
    marks = "#" * level
    return [
        re.sub(r"^\d+(\.\d+)*\.?\s+", "", h).strip()
        for h in re.findall(rf"^{marks}\s+(.+?)\s*$", text, re.M)
    ]


def section_body(text, title):
    """The body of the `## title` section, up to the next `## ` heading."""
    m = re.search(rf"^##\s+{re.escape(title)}\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    return m[1] if m else ""


def table_first_cells(text):
    """The first cell of each body row of the Markdown tables in text."""
    cells = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cell = line.split("|")[1].strip().strip("*`").strip()
        if cell and not re.fullmatch(r":?-+:?", cell):
            cells.append(cell)
    # Drop each table's header row (the row above its |---| separator).
    lines = [ln for ln in text.splitlines() if ln.startswith("|")]
    headers = {
        ln.split("|")[1].strip().strip("*`").strip()
        for ln, nxt in zip(lines, lines[1:], strict=False)
        if re.match(r"\|\s*:?-+", nxt)
    }
    return [c for c in cells if c not in headers]


def check_dsp(fx, dsp, where=None):
    where = where or f"src/{fx}.dsp"
    problems = []
    code = strip_comments(dsp.read_text())

    decl = declares(code)
    for key in REQUIRED_DECLARES:
        if not decl.get(key):
            problems.append(f'{where}: no `declare {key} "...";`')
    version = decl.get("version")
    if version and not re.fullmatch(r"\d+\.\d+\.\d+", version):
        problems.append(f"{where}: version {version!r} is not major.minor.micro")

    for m in re.finditer(r"\b(" + "|".join(SMOOTHED_CONTROLS) + r')\s*\(\s*"([^"]*)"', code):
        kind, label = m.groups()
        name = re.sub(r"\[[^]]*\]", "", label).strip()
        if kind in RANGED_CONTROLS and "[unit:" not in label:
            problems.append(f"{where}: control {name!r} has no [unit:...]")
        end = code.find(";", m.end())
        if "si.smoo" not in code[m.end() : end if end >= 0 else None]:
            problems.append(f"{where}: control {name!r} is not smoothed with si.smoo")

    if "oversample4" in code and not re.search(
        r'hbargraph\s*\(\s*"Latency\b[^"]*\[lv2:reportsLatency\]', code
    ):
        problems.append(
            f"{where}: uses oversample4 but reports no latency "
            '(attach hbargraph("Latency [unit:samples] [lv2:reportsLatency] '
            '[lv2:integer]", 0, 256))'
        )
    if not re.search(r"\bpk\.safety\s*\(", code):
        problems.append(f"{where}: output does not go through pk.safety")
    return problems, decl.get("version"), "oversample4" in code


def check_docs(root, fx, version):
    problems = []
    docs = root / "docs" / fx
    notes = [p for p in ("design-notes.md", "circuit-notes.md") if (docs / p).exists()]
    if not notes:
        problems.append(f"docs/{fx}/: no design-notes.md or circuit-notes.md")
    for page in notes:
        found = headings((docs / page).read_text())
        for section in NOTES_SECTIONS[page]:
            if not any(h.lower().startswith(section.lower()) for h in found):
                problems.append(f"docs/{fx}/{page}: no `## {section}` section")
    if not (docs / "index.md").exists():
        problems.append(f"docs/{fx}/index.md is missing")
    elif f"<!-- downloads:{fx} -->" not in (docs / "index.md").read_text():
        problems.append(
            f"docs/{fx}/index.md: no `<!-- downloads:{fx} -->` marker for the download links"
        )
    changelog = docs / "changelog.md"
    if not changelog.exists():
        problems.append(f"docs/{fx}/changelog.md is missing")
    elif version and not re.search(rf"^## \[{re.escape(version)}\]", changelog.read_text(), re.M):
        problems.append(f"docs/{fx}/changelog.md: no `## [{version}]` section")

    for path, needle in (
        ("README.md", f"`src/{fx}.dsp`"),
        ("docs/index.md", f"({fx}/index.md)"),
        ("docs/effects/index.md", f"(../{fx}/index.md)"),
    ):
        if needle not in (root / path).read_text():
            problems.append(f"{path}: no effect table row linking {needle.strip('()`')}")

    nav = (root / "mkdocs.yml").read_text().partition("\nnav:")[2]
    for page in ("index.md", "changelog.md", *notes):
        if not re.search(rf"[\s:]{re.escape(fx)}/{re.escape(page)}\s*$", nav, re.M):
            problems.append(f"mkdocs.yml: {fx}/{page} is not in nav")
    return problems


def check_page(root, fx, code):
    """The effect page's sections, controls, presets and plot data links."""
    page = root / "docs" / fx / "index.md"
    if not page.exists():
        return []  # reported by check_docs
    where = f"docs/{fx}/index.md"
    text = page.read_text()
    problems = []

    presets_toml = root / "src" / f"{fx}.presets.toml"
    presets = []
    if presets_toml.exists():
        try:
            presets = [p["name"] for p in tomllib.loads(presets_toml.read_text())["preset"]]
        except (tomllib.TOMLDecodeError, KeyError, TypeError) as e:
            problems.append(f"src/{fx}.presets.toml: cannot read the preset names ({e})")

    found = headings(text)
    for section in (*PAGE_SECTIONS, *(("Presets",) if presets_toml.exists() else ())):
        if section not in found:
            problems.append(f"{where}: no `## {section}` section")

    # The Controls table lists exactly the controls a player sets, by label;
    # bargraphs (the reported latency) are read-only outputs.
    bargraphs = set(re.findall(r'\b[hv]bargraph\s*\(\s*"([^"\[]*)', code))
    controls = [c for c in control_labels(code) if c not in bargraphs]
    rows = table_first_cells(section_body(text, "Controls"))
    for label in controls:
        if label not in rows:
            problems.append(f"{where}: control {label!r} has no row in the Controls table")
    for row in rows:
        if row not in controls:
            problems.append(f"{where}: the Controls table lists {row!r}, which is not a control")
    listed = section_body(text, "Presets")
    for name in presets:
        if name not in listed:
            problems.append(f"{where}: preset {name!r} is not listed under Presets")
    return problems


# An embedded measurement plot, and the CSV data next to it.
FIGURE = re.compile(r"!\[[^]]*\]\(\.\./measurements/([\w-]+)/([\w.-]+\.svg)\)")
DATA = re.compile(r"\(\.\./measurements/[\w-]+/[\w.-]+\.csv\)")


def check_plot_data(root, fx):
    """Every measurement plot in the effect's pages links the CSV behind it:
    some `../measurements/.../*.csv` link before the next plot or heading."""
    problems = []
    for page in sorted((root / "docs" / fx).glob("*.md")):
        lines = page.read_text().splitlines()
        for i, line in enumerate(lines):
            for m in FIGURE.finditer(line):
                rest = []
                for nxt in lines[i + 1 :]:
                    if nxt.startswith("#") or FIGURE.search(nxt):
                        break
                    rest.append(nxt)
                if not DATA.search(line[m.end() :] + "\n" + "\n".join(rest)):
                    problems.append(
                        f"docs/{fx}/{page.name}:{i + 1}: plot {m[2]} has no link to "
                        "the CSV data behind it"
                    )
    return problems


def sheet_files(root, fx):
    """The SVG file names `make schematics` gives the root sheet and each
    sub-sheet named in the effect's root schematic."""
    sch = root / "docs" / fx / "schematics" / f"{fx}.kicad_sch"
    if not sch.exists():
        return []
    names = re.findall(r'\(property\s+"Sheet ?name"\s+"([^"]*)"', sch.read_text())
    return [f"{fx}.svg"] + [f"{fx}-{n.lower().replace(' ', '-')}.svg" for n in names]


def check_schematic_docs(root, fx):
    """With circuit notes, the root sheet is on the effect page and every
    sheet is embedded somewhere in the effect's docs (AGENTS.md, step 6)."""
    docs = root / "docs" / fx
    if not (docs / "circuit-notes.md").exists():
        return []
    sheets = sheet_files(root, fx)
    if not sheets:
        return []  # a missing schematic is reported by schematics-present
    problems = []
    index = docs / "index.md"
    if index.exists() and f"../schematics/{fx}/{fx}.svg" not in index.read_text():
        problems.append(
            f"docs/{fx}/index.md: root schematic sheet ../schematics/{fx}/{fx}.svg is not embedded"
        )
    text = "\n".join(p.read_text() for p in sorted(docs.glob("*.md")))
    for sheet in sheets[1:]:
        if f"../schematics/{fx}/{sheet}" not in text:
            problems.append(
                f"docs/{fx}/: schematic sheet ../schematics/{fx}/{sheet} is not embedded"
            )
    return problems


def check_tests(root, fx, oversamples):
    tests = root / "tests" / fx
    if not tests.is_dir():
        return [f"tests/{fx}/ is missing"]
    problems = []
    for name in MINIMUM_TESTS:
        if not (tests / name).exists():
            problems.append(f"tests/{fx}/{name} is missing")
    if (root / "src" / f"{fx}.presets.toml").exists() and not (tests / "test_presets.py").exists():
        problems.append(f"tests/{fx}/test_presets.py is missing (src/{fx}.presets.toml exists)")
    scripts = sorted(tests.glob("test_*.py"))
    for script in scripts:
        if not re.search(r"^\s*finish\(\)", script.read_text(), re.M):
            problems.append(f"tests/{fx}/{script.name}: does not end with finish()")
    if oversamples and not any("RENDER_1X" in s.read_text() for s in scripts):
        problems.append(f"tests/{fx}/: oversamples but no test compares against RENDER_1X")
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path, default=ROOT, help="repository root")
    ap.add_argument(
        "--dsp-only", action="store_true", help="only the DSP checks, on .dsp file paths"
    )
    ap.add_argument(
        "names", nargs="*", help="effects to check (default: all), or files with --dsp-only"
    )
    args = ap.parse_args()
    root = args.root

    if args.dsp_only:
        problems = []
        for path in map(Path, args.names):
            problems += check_dsp(path.stem, path, where=str(path))[0]
        for p in problems:
            print(p)
        return 1 if problems else 0

    effects = args.names or sorted(p.stem for p in (root / "src").glob("*.dsp"))
    problems = []
    for fx in effects:
        dsp = root / "src" / f"{fx}.dsp"
        if not dsp.exists():
            problems.append(f"src/{fx}.dsp is missing")
            continue
        dsp_problems, version, oversamples = check_dsp(fx, dsp)
        problems += dsp_problems
        problems += check_docs(root, fx, version)
        problems += check_page(root, fx, strip_comments(dsp.read_text()))
        problems += check_plot_data(root, fx)
        problems += check_schematic_docs(root, fx)
        problems += check_tests(root, fx, oversamples)

    for p in problems:
        print(p)
    if problems:
        print("See AGENTS.md, 'Adding a new effect'.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
