#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Fail if an effect is missing anything the new-effect checklist requires.

Usage: check-effects.py [--root DIR] [NAME...]

For every src/<name>.dsp (or only the NAMEs given), checks the parts of the
checklist in AGENTS.md ("Adding a new effect") that can be checked without
compiling anything:

* the DSP: the required `declare`s, a `major.minor.micro` version, a unit and
  si.smoo smoothing on every control, a Latency bargraph tagged
  [lv2:reportsLatency] whenever it uses pk.oversample4, and pk.safety on the
  output
* the notes: docs/<name>/design-notes.md or circuit-notes.md
* the docs: docs/<name>/index.md, docs/<name>/changelog.md with a section for
  the declared version, rows in README.md, docs/index.md and
  docs/effects/index.md, and the pages in the mkdocs.yml nav
* the tests: tests/<name>/ with the minimum set (test_silence.py,
  test_peak.py, test_freqresp.py, test_harmonics.py), an aliasing comparison
  against RENDER_1X when the effect oversamples, test_presets.py when it has
  presets, and a finish() call in every script

Whether the effect compiles, passes its tests and has a schematic is checked
elsewhere (faust-compile, make test, schematics-present). Used by the
effect-checklist pre-commit hook.
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DECLARES = ("name", "description", "author", "license", "version", "lv2class")
MINIMUM_TESTS = ("test_silence.py", "test_peak.py", "test_freqresp.py", "test_harmonics.py")
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


def check_dsp(fx, dsp):
    problems = []
    code = strip_comments(dsp.read_text())

    decl = declares(code)
    for key in REQUIRED_DECLARES:
        if not decl.get(key):
            problems.append(f'src/{fx}.dsp: no `declare {key} "...";`')
    version = decl.get("version")
    if version and not re.fullmatch(r"\d+\.\d+\.\d+", version):
        problems.append(f"src/{fx}.dsp: version {version!r} is not major.minor.micro")

    for m in re.finditer(r"\b(" + "|".join(SMOOTHED_CONTROLS) + r')\s*\(\s*"([^"]*)"', code):
        kind, label = m.groups()
        name = re.sub(r"\[[^]]*\]", "", label).strip()
        if kind in RANGED_CONTROLS and "[unit:" not in label:
            problems.append(f"src/{fx}.dsp: control {name!r} has no [unit:...]")
        end = code.find(";", m.end())
        if "si.smoo" not in code[m.end() : end if end >= 0 else None]:
            problems.append(f"src/{fx}.dsp: control {name!r} is not smoothed with si.smoo")

    if "oversample4" in code and not re.search(
        r'hbargraph\s*\(\s*"Latency\b[^"]*\[lv2:reportsLatency\]', code
    ):
        problems.append(
            f"src/{fx}.dsp: uses oversample4 but reports no latency "
            '(attach hbargraph("Latency [unit:samples] [lv2:reportsLatency] '
            '[lv2:integer]", 0, 256))'
        )
    if not re.search(r"\bpk\.safety\s*\(", code):
        problems.append(f"src/{fx}.dsp: output does not go through pk.safety")
    return problems, decl.get("version"), "oversample4" in code


def check_docs(root, fx, version):
    problems = []
    docs = root / "docs" / fx
    notes = [p for p in ("design-notes.md", "circuit-notes.md") if (docs / p).exists()]
    if not notes:
        problems.append(f"docs/{fx}/: no design-notes.md or circuit-notes.md")
    if not (docs / "index.md").exists():
        problems.append(f"docs/{fx}/index.md is missing")
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
    ap.add_argument("names", nargs="*", help="effects to check (default: all)")
    args = ap.parse_args()
    root = args.root

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
        problems += check_tests(root, fx, oversamples)

    for p in problems:
        print(p)
    if problems:
        print("See AGENTS.md, 'Adding a new effect'.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
