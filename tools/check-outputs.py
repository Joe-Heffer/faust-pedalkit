#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Fail if a built output that an effect's plugins or docs rely on is missing.

Usage: check-outputs.py KIND[,KIND...] [NAME...]

Run after the targets that make the outputs; tools/check-effects.py checks
everything that can be checked from the sources alone. KIND is one or more of:

* measurements (after `make test`): tests/out/<name>/ holds at least one SVG
  plot and one CSV, no SVG or CSV is empty, every CSV has a header and at
  least one row, and every `measurements/<name>/<file>` the docs embed or
  link was written by the tests
* schematics (after `make schematics`): for every effect with a schematic,
  build/schematics/<name>/ holds a sheet, every `schematics/<name>/<file>`
  the docs embed was rendered, and every rendered sheet is embedded in the
  docs
* lv2 (after `make lv2`): build/<name>.lv2/ holds manifest.ttl, <name>.ttl and
  the shared object, and, when src/<name>.presets.toml exists, presets.ttl
  with one preset per [[preset]], each listed in manifest.ttl
* vst3 (after `make vst3`): build/<name>.vst3/ holds a Linux shared object
* clap (after `make clap`): build/<name>.clap is a shared object

NAMEs default to every src/*.dsp. `make check-outputs OUTPUTS=<kinds>` runs
this, and CI runs it after each build and test step.
"""

import argparse
import csv
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KINDS = ("measurements", "schematics", "lv2", "vst3", "clap")
ELF = b"\x7fELF"


def doc_refs(root, kind, fx):
    """{file name: [docs page:line, ...]} for every `<kind>/<fx>/<file>`
    referenced from the documentation."""
    refs = {}
    pattern = re.compile(rf"\b{kind}/{re.escape(fx)}/([\w.-]+\.(?:svg|csv))\b")
    for page in sorted((root / "docs").rglob("*.md")):
        for n, line in enumerate(page.read_text().splitlines(), 1):
            for name in pattern.findall(line):
                refs.setdefault(name, []).append(f"{page.relative_to(root)}:{n}")
    return refs


def check_measurements(root, fx):
    out = root / "tests" / "out" / fx
    where = f"tests/out/{fx}"
    if not out.is_dir():
        return [f"{where}/ is missing; run `make test FX={fx}`"]
    problems = []
    svgs = sorted(out.glob("*.svg"))
    csvs = sorted(out.glob("*.csv"))
    if not svgs:
        problems.append(f"{where}/: no SVG plots")
    if not csvs:
        problems.append(f"{where}/: no CSV data")
    for path in svgs:
        if path.stat().st_size == 0 or b"<svg" not in path.read_bytes()[:4096]:
            problems.append(f"{where}/{path.name}: not an SVG image")
    for path in csvs:
        with path.open(newline="") as f:
            rows = list(csv.reader(f))
        if len(rows) < 2:
            problems.append(f"{where}/{path.name}: no data rows under the header")
    for name, pages in sorted(doc_refs(root, "measurements", fx).items()):
        if not (out / name).exists():
            problems.append(
                f"{pages[0]}: links measurements/{fx}/{name}, but the tests did not write "
                f"{where}/{name}"
            )
    return problems


def check_schematics(root, fx):
    if not (root / "docs" / fx / "schematics" / f"{fx}.kicad_sch").exists():
        return []  # no schematic: tools/check-schematics.py says whether one is needed
    out = root / "build" / "schematics" / fx
    where = f"build/schematics/{fx}"
    rendered = sorted(p.name for p in out.glob("*.svg")) if out.is_dir() else []
    if not rendered:
        return [f"{where}/: no rendered sheets; run `make schematics FX={fx}`"]
    problems = []
    refs = doc_refs(root, "schematics", fx)
    for name, pages in sorted(refs.items()):
        if name not in rendered:
            problems.append(
                f"{pages[0]}: embeds schematics/{fx}/{name}, but `make schematics` did not "
                f"render {where}/{name}"
            )
    for name in rendered:
        if name not in refs:
            problems.append(f"docs/{fx}/: schematic sheet {name} is not embedded in the docs")
    return problems


def preset_names(root, fx):
    toml = root / "src" / f"{fx}.presets.toml"
    if not toml.exists():
        return []
    return [p["name"] for p in tomllib.loads(toml.read_text()).get("preset", [])]


def is_elf(path):
    try:
        with path.open("rb") as f:
            return f.read(4) == ELF
    except OSError:
        return False


def check_lv2(root, fx):
    bundle = root / "build" / f"{fx}.lv2"
    where = f"build/{fx}.lv2"
    if not bundle.is_dir():
        return [f"{where}/ is missing; run `make lv2 FX={fx}`"]
    problems = []
    for name in ("manifest.ttl", f"{fx}.ttl"):
        if not (bundle / name).is_file():
            problems.append(f"{where}/{name} is missing")
    if not any(is_elf(p) for p in bundle.glob("*.so")):
        problems.append(f"{where}/: no plugin shared object")
    presets = preset_names(root, fx)
    if presets:
        ttl = bundle / "presets.ttl"
        manifest = bundle / "manifest.ttl"
        if not ttl.is_file():
            problems.append(f"{where}/presets.ttl is missing (src/{fx}.presets.toml exists)")
        else:
            labels = re.findall(r'rdfs:label\s+"((?:[^"\\]|\\.)*)"', ttl.read_text())
            for name in presets:
                if name not in labels:
                    problems.append(f"{where}/presets.ttl: no preset {name!r}")
        if manifest.is_file():
            listed = manifest.read_text().count("rdfs:seeAlso <presets.ttl>")
            if listed != len(presets):
                problems.append(
                    f"{where}/manifest.ttl: lists {listed} presets, "
                    f"src/{fx}.presets.toml has {len(presets)}"
                )
    return problems


def check_vst3(root, fx):
    bundle = root / "build" / f"{fx}.vst3"
    where = f"build/{fx}.vst3"
    if not bundle.is_dir():
        return [f"{where}/ is missing; run `make vst3 FX={fx}`"]
    if not any(is_elf(p) for p in bundle.glob("Contents/*-linux/*.so")):
        return [f"{where}/: no Contents/<arch>-linux/*.so"]
    return []


def check_clap(root, fx):
    plugin = root / "build" / f"{fx}.clap"
    if not plugin.exists():
        return [f"build/{fx}.clap is missing; run `make clap FX={fx}`"]
    if not is_elf(plugin):
        return [f"build/{fx}.clap is not a shared object"]
    return []


CHECKS = {
    "measurements": check_measurements,
    "schematics": check_schematics,
    "lv2": check_lv2,
    "vst3": check_vst3,
    "clap": check_clap,
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("kinds", help=f"comma- or space-separated, from: {', '.join(KINDS)}")
    ap.add_argument("names", nargs="*", help="effects to check (default: all)")
    ap.add_argument("--root", type=Path, default=ROOT, help="repository root")
    args = ap.parse_args()
    root = args.root

    kinds = [k for k in re.split(r"[,\s]+", args.kinds) if k]
    unknown = [k for k in kinds if k not in CHECKS]
    if unknown or not kinds:
        given = ", ".join(unknown) or "(none)"
        ap.error(f"unknown output kind(s) {given}; choose from {', '.join(KINDS)}")
    effects = args.names or sorted(p.stem for p in (root / "src").glob("*.dsp"))

    problems = []
    for kind in kinds:
        for fx in effects:
            problems += CHECKS[kind](root, fx)
    for p in problems:
        print(p)
    if problems:
        print("See AGENTS.md, 'Adding a new effect'.")
    else:
        print(f"outputs present ({', '.join(kinds)}): {', '.join(effects)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
