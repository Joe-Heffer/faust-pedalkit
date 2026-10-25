#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Print the release tags that are due: one `<name>-vX.Y.Z` per line.

Usage: untagged.py

An effect is due when its `declare version` has no tag yet and
tools/release/release-info.py accepts the tag (the effect exists and
docs/<name>/changelog.md has a `## [X.Y.Z]` section). An effect whose version
has no changelog section is skipped with a warning on stderr, so merging a
version bump before its changelog does not release anything.
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dspmeta import declares  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
INFO = Path(__file__).resolve().parent / "release-info.py"


def main():
    existing = set(
        subprocess.run(
            ["git", "tag", "--list"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.split()
    )
    for dsp in sorted((ROOT / "src").glob("*.dsp")):
        version = declares(dsp).get("version")
        tag = f"{dsp.stem}-v{version}"
        if tag in existing:
            continue
        check = subprocess.run([sys.executable, INFO, tag], capture_output=True, text=True)
        if check.returncode:
            print(f"Not tagging {tag}: {check.stderr.strip()}", file=sys.stderr)
            continue
        print(tag)


if __name__ == "__main__":
    main()
