#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Generate each effect's KiCad schematic from tools/schematics/<name>.py.

Usage:
    python3 tools/schematics/build.py [--check] [--out DIR] [NAME ...]

Without names, every effect with a script is generated. Each script defines
`project()`, which returns a kicadsch.Project; its files are written to
docs/<name>/schematics/ (or DIR/<name>/ with --out).

--check writes nothing into docs/. It generates into build/schematics-check/
and fails if any committed file differs, or if an effect with circuit notes
has no schematic script. CI runs it (make schematic-check) so the committed
.kicad_sch files never drift from their scripts.

Generation reads the stock KiCad symbol libraries (KICAD_SYMBOL_DIR, default
/usr/share/kicad/symbols), so run it where KiCad is installed or in the docs
image (Dockerfile.docs).
"""

import argparse
import filecmp
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def scripts():
    return sorted(
        p.stem for p in HERE.glob("*.py") if p.stem not in ("build", "kicadsch", "stages")
    )


def load(name):
    spec = importlib.util.spec_from_file_location(f"schematic_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.project()


def write(name, out):
    out.mkdir(parents=True, exist_ok=True)
    files = load(name).files()
    for old in out.glob("*.kicad_sch"):
        if old.name not in files:
            old.unlink()
    for fname, text in files.items():
        (out / fname).write_text(text, encoding="utf-8")
    return files


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--check", action="store_true", help="fail if a committed schematic is stale")
    ap.add_argument("--out", type=Path, help="write DIR/<name>/ instead of docs/<name>/schematics/")
    ap.add_argument("names", nargs="*")
    args = ap.parse_args()

    have = scripts()
    names = args.names or have
    status = 0

    # Every effect with circuit notes has a schematic (AGENTS.md, step 6).
    for notes in sorted(ROOT.glob("docs/*/circuit-notes.md")):
        fx = notes.parent.name
        if fx not in have and (not args.names or fx in args.names):
            print(f"{fx}: has circuit notes but no tools/schematics/{fx}.py")
            status = 1

    for name in names:
        if name not in have:
            print(f"{name}: no tools/schematics/{name}.py")
            status = 1
            continue
        committed = ROOT / "docs" / name / "schematics"
        if args.check:
            out = ROOT / "build" / "schematics-check" / name
            files = write(name, out)
            stale = [
                f
                for f in files
                if not (committed / f).exists()
                or not filecmp.cmp(out / f, committed / f, shallow=False)
            ]
            extra = [p.name for p in committed.glob("*.kicad_sch") if p.name not in files]
            if stale or extra:
                for f in stale:
                    print(f"{name}: docs/{name}/schematics/{f} is stale or missing")
                for f in extra:
                    print(f"{name}: docs/{name}/schematics/{f} has no counterpart in the script")
                print(f"{name}: run `make schematic-sources FX={name}` and commit the result")
                status = 1
            else:
                print(f"{name}: schematic up to date ({len(files)} files)")
        else:
            out = args.out / name if args.out else committed
            files = write(name, out)
            print(
                f"{name}: wrote {len(files)} files to {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}"
            )
    return status


if __name__ == "__main__":
    sys.exit(main())
