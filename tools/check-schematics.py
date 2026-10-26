#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Fail if an effect with circuit notes has no schematic.

Usage: check-schematics.py

Every effect that borrows from a circuit (it has docs/<name>/circuit-notes.md)
needs a generator script, tools/schematics/<name>.py, and the schematic it
writes, docs/<name>/schematics/<name>.kicad_sch and <name>.kicad_pro. This
check needs no KiCad, so it runs as a pre-commit hook. Whether the committed
files match their script is checked by `make schematic-check`, which needs
the KiCad symbol libraries and runs in the docs workflow.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    missing = []
    for notes in sorted(ROOT.glob("docs/*/circuit-notes.md")):
        fx = notes.parent.name
        for path in (
            Path("tools/schematics") / f"{fx}.py",
            Path("docs") / fx / "schematics" / f"{fx}.kicad_sch",
            Path("docs") / fx / "schematics" / f"{fx}.kicad_pro",
        ):
            if not (ROOT / path).exists():
                missing.append((fx, path))
    for fx, path in missing:
        print(f"{fx}: has circuit notes but no {path} (see docs/development/schematics.md)")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
