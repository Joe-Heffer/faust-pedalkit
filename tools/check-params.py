#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Fail if a released effect's controls were renamed, retyped or reordered.

Usage: check-params.py [DSP...]   (default: every src/*.dsp)

Hosts save a plug-in's settings by parameter position: the VST3 and CLAP
wrappers number the controls in UI order (the [n] prefixes) and store their
plain values in that order, and LV2 stores them by port symbol, which
faust2lv2 builds from the label and the index. So once an effect is released,
its controls at that release must keep their label, type and place, or old
projects and presets load the wrong values. New controls go at the end.

Each effect is compared with its latest `<name>-vX.Y.Z` tag. Effects with no
tag yet, or a checkout without tags, pass with a note. Used by the
params-stable pre-commit hook; the CI lint job fetches the tags for it.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTROL = re.compile(r'\b(hslider|vslider|nentry|checkbox|button)\s*\(\s*"([^"]*)"')
ORDER = re.compile(r"\[(\d+)\]")
META = re.compile(r"\[[^\]]*\]")
TAG = re.compile(r"-v(\d+)\.(\d+)\.(\d+)$")


def controls(source):
    """(type, label) of each input control, in UI order."""
    found = []
    for pos, m in enumerate(CONTROL.finditer(source)):
        kind, text = m.groups()
        order = ORDER.search(text)
        label = " ".join(META.sub("", text).split())
        found.append((int(order.group(1)) if order else 10**6, pos, kind, label))
    return [(kind, label) for _, _, kind, label in sorted(found)]


def git(*args):
    res = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    return res.stdout if res.returncode == 0 else None


def latest_tag(name):
    tags = (git("tag", "--list", f"{name}-v*") or "").split()
    versions = [(tuple(map(int, m.groups())), t) for t in tags if (m := TAG.search(t))]
    return max(versions)[1] if versions else None


def check(path):
    name = path.stem
    tag = latest_tag(name)
    if tag is None:
        print(f"{name}: no release tag, nothing to compare")
        return []
    old_src = git("show", f"{tag}:src/{name}.dsp")
    if old_src is None:
        return [f"{name}: src/{name}.dsp is missing from {tag}"]
    old, new = controls(old_src), controls(path.read_text())
    errors = []
    for i, before in enumerate(old):
        after = new[i] if i < len(new) else None
        if after != before:
            now = f"{after[0]} '{after[1]}'" if after else "nothing"
            errors.append(
                f"{name}: parameter {i} was {before[0]} '{before[1]}' in {tag}, now {now}. "
                "Released controls keep their label, type and place; add new ones at the end."
            )
    return errors


def main(argv):
    paths = [Path(p) for p in argv] or sorted((ROOT / "src").glob("*.dsp"))
    if git("rev-parse", "--git-dir") is None:
        print("not a git checkout, skipping")
        return 0
    if not (git("tag", "--list") or "").strip():
        print("no tags in this checkout (fetch them with `git fetch --tags`), skipping")
        return 0
    errors = [e for p in paths if p.suffix == ".dsp" for e in check(p)]
    for e in errors:
        print(e, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
