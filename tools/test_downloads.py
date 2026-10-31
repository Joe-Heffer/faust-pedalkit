#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Check how tools/downloads.py picks releases and writes links (no network)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import downloads  # noqa: E402

BASE = "https://example.test/dl/"


def release(tag, names, **flags):
    return {
        "tag_name": tag,
        "html_url": f"https://example.test/{tag}",
        "assets": [{"name": n, "browser_download_url": BASE + n} for n in names],
        **flags,
    }


def assets_for(name, version):
    stem = f"{name}-{version}-linux-x86_64"
    return [
        f"{stem}.tar.gz",
        f"{stem}-clap.tar.gz",
        f"{stem}-vst3.tar.gz",
        f"{stem}-lv2.tar.gz",
        "SHA256SUMS",
    ]


releases = [
    release("bassdrive-v0.1.0", assets_for("bassdrive", "0.1.0")),
    release("bassdrive-v0.10.0", assets_for("bassdrive", "0.10.0")),
    release("bassdrive-v0.9.0", assets_for("bassdrive", "0.9.0")),
    release("midhump-v0.2.0", assets_for("midhump", "0.2.0"), draft=True),
    release("midhump-v0.1.0", assets_for("midhump", "0.1.0"), prerelease=True),
    # Releases from before per-format archives: only the combined tarball.
    release("bassgrit-v0.1.0", ["bassgrit-0.1.0-linux-x86_64.tar.gz", "SHA256SUMS"]),
    release("not-a-tag", []),
]

latest = downloads.latest_by_effect(releases)
assert set(latest) == {"bassdrive", "bassgrit"}, latest
assert latest["bassdrive"]["tag_name"] == "bassdrive-v0.10.0", "versions compare as numbers"

md = downloads.block("bassdrive", "BassDrive", latest["bassdrive"])
assert "Download BassDrive 0.10.0 (CLAP)" in md, md
assert md.index("-clap.tar.gz") < md.index("-vst3.tar.gz"), md
assert BASE + "bassdrive-0.10.0-linux-x86_64-lv2.tar.gz" in md and BASE + "SHA256SUMS" in md, md

md = downloads.block("bassgrit", "BassGrit", latest["bassgrit"])
assert BASE + "bassgrit-0.1.0-linux-x86_64.tar.gz" in md and "-clap.tar.gz" not in md, md

md = downloads.block("midhump", "MidHump", latest.get("midhump"))
assert "No release of MidHump is published yet" in md and downloads.RELEASES_PAGE in md, md

table = downloads.table([("bassdrive", "BassDrive"), ("midhump", "MidHump")], latest)
assert "| **MidHump** | not yet published | – | – | – | – |" in table, table
assert downloads.latest_by_effect(None) == {}
print("downloads: ok")
