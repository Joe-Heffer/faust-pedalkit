#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Check a release tag against its effect and print what the release needs.

Usage: release-info.py TAG [NOTES_FILE]

Each effect is released on its own, under a tag `<name>-v<X.Y.Z>`, e.g.
`bassdrive-v0.1.0`. This fails unless src/<name>.dsp exists, its
`declare version` is X.Y.Z, and docs/<name>/changelog.md has a section
`## [X.Y.Z]`. On success it prints `fx=`, `version=` and `title=` lines (the
format of $GITHUB_OUTPUT) and, given NOTES_FILE, writes that changelog
section to it for the release notes.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dspmeta import declares  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
TAG = re.compile(r"^(?P<name>[a-z0-9_]+)-v(?P<version>\d+\.\d+\.\d+)$")


def changelog_section(text, version):
    """Return the body of the `## [version]` section, or None if it is missing."""
    lines = text.splitlines()
    heading = re.compile(rf"^## \[{re.escape(version)}\]")
    for i, line in enumerate(lines):
        if heading.match(line):
            body = []
            for rest in lines[i + 1 :]:
                # The next version, or the link references at the end.
                if rest.startswith("## ") or re.match(r"^\[[^\]]+\]: ", rest):
                    break
                body.append(rest)
            return "\n".join(body).strip() + "\n"
    return None


def main(argv):
    if len(argv) not in (2, 3):
        sys.exit(__doc__)
    tag = argv[1]
    m = TAG.match(tag)
    if not m:
        sys.exit(f"Tag {tag!r} is not <name>-v<X.Y.Z>, e.g. bassdrive-v0.1.0")
    name, version = m["name"], m["version"]

    dsp = ROOT / "src" / f"{name}.dsp"
    if not dsp.is_file():
        effects = sorted(p.stem for p in (ROOT / "src").glob("*.dsp"))
        sys.exit(f"Tag {tag}: no effect {name!r}. Effects: {' '.join(effects)}")
    meta = declares(dsp)
    if meta.get("version") != version:
        sys.exit(f"Tag {tag}: {dsp.relative_to(ROOT)} declares version {meta.get('version')}")

    changelog = ROOT / "docs" / name / "changelog.md"
    if not changelog.is_file():
        sys.exit(f"Tag {tag}: {changelog.relative_to(ROOT)} is missing")
    notes = changelog_section(changelog.read_text(), version)
    if notes is None:
        sys.exit(f"Tag {tag}: {changelog.relative_to(ROOT)} has no '## [{version}]' section")

    print(f"fx={name}")
    print(f"version={version}")
    print(f"title={meta.get('name', name)} {version}")
    if len(argv) == 3:
        Path(argv[2]).write_text(notes)


if __name__ == "__main__":
    main(sys.argv)
