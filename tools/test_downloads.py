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
assert "[Download BassDrive 0.10.0](" + BASE + "bassdrive-0.10.0-linux-x86_64.tar.gz)" in md, md
assert md.index("-clap.tar.gz") < md.index("-vst3.tar.gz"), md
assert BASE + "bassdrive-0.10.0-linux-x86_64-lv2.tar.gz" in md and BASE + "SHA256SUMS" in md, md

md = downloads.block("bassgrit", "BassGrit", latest["bassgrit"])
assert BASE + "bassgrit-0.1.0-linux-x86_64.tar.gz" in md and "-clap.tar.gz" not in md, md

md = downloads.block("midhump", "MidHump", latest.get("midhump"))
assert "MidHump has no published release yet" in md and downloads.RELEASES_PAGE in md, md
assert "(../demo/index.html?fx=midhump)" in md and "(../install.md)" in md, md

md = downloads.button("bassdrive", "BassDrive", latest["bassdrive"])
assert md.startswith("[Download 0.10.0](" + BASE + "bassdrive-0.10.0-linux-x86_64.tar.gz)"), md
md = downloads.button("x", "X", release("x-v1.0.0", ["x-1.0.0-linux-x86_64-clap.tar.gz"]))
assert md.startswith("[Download 1.0.0 (CLAP)](" + BASE + "x-1.0.0-linux-x86_64-clap.tar.gz)"), md
md = downloads.button("bassgrit", "BassGrit", latest["bassgrit"])
assert "(" + BASE + "bassgrit-0.1.0-linux-x86_64.tar.gz)" in md, md
md = downloads.button("midhump", "MidHump", latest.get("midhump"))
assert "(demo/index.html?fx=midhump)" in md and "Not released yet" in md, md

fx = [("bassdrive", "BassDrive", "Overdrive"), ("midhump", "MidHump", "Mids")]
table = downloads.table(fx, latest)
row = "| **[MidHump](midhump/index.md)**<br>Mids | – | not released yet |"
assert row in table and "(demo/index.html?fx=midhump)" in table, table
row = "| **[BassDrive](bassdrive/index.md)**<br>Overdrive | 0.10.0 | **[All formats](" + BASE
assert row in table and "[CLAP](" + BASE + "bassdrive-0.10.0-linux-x86_64-clap" in table, table
assert downloads.latest_by_effect(None) == {}
print("downloads: ok")
