# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Download links for the website, from the repository's published releases.

Each effect is released on its own, under a tag `<name>-vX.Y.Z`. GitHub's
`releases/latest` is repo-wide, so it cannot name the latest release of one
effect. This finds, for each effect, the newest published (neither draft nor
pre-release) release and links its assets:

  <name>-<version>-linux-<arch>.tar.gz          all formats, with install.sh
  <name>-<version>-linux-<arch>-clap.tar.gz     one format each (clap, vst3, lv2),
                                                if a release has them
  SHA256SUMS

tools/mkdocs_hooks.py swaps the markers in the pages for the Markdown made
here: `<!-- downloads:<name> -->` (an effect page's download block),
`<!-- downloads:all -->` (the table on the Download page) and
`<!-- download-button:<name> -->` (one button, for the effect cards). If no
release is published yet, or GitHub cannot be reached (an offline build), the
links offer the browser demo and the releases page instead, so they never 404.

`base` is the relative path from the page to the site root ("" or "../"), so
the same Markdown works on the home page and on an effect page.
"""

import json
import os
import re
import urllib.request

REPO = "Joe-Heffer/faust-pedalkit"
RELEASES_PAGE = f"https://github.com/{REPO}/releases"
API = f"https://api.github.com/repos/{REPO}/releases?per_page=100"
# CLAP first: the newest and the most open of the three formats.
FORMATS = (("clap", "CLAP"), ("vst3", "VST3"), ("lv2", "LV2"))
TAG = re.compile(r"^(?P<name>[a-z0-9_]+)-v(?P<version>\d+)\.(\d+)\.(\d+)$")
ALL_ASSET = re.compile(r"-linux-[^-]+\.tar\.gz$")


def fetch_releases():
    """Return the repository's releases from the GitHub API, or None if unreachable."""
    request = urllib.request.Request(API, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)
    except (OSError, ValueError):
        return None


def latest_by_effect(releases):
    """Map each effect to its newest published release, by version number."""
    newest = {}
    for release in releases or []:
        if release.get("draft") or release.get("prerelease"):
            continue
        m = TAG.match(release.get("tag_name", ""))
        if not m:
            continue
        key = tuple(int(g) for g in m.groups()[1:])
        if m["name"] not in newest or key > newest[m["name"]][0]:
            newest[m["name"]] = (key, release)
    return {name: release for name, (_, release) in newest.items()}


def assets(release):
    """Pick a release's download URLs: `clap`/`vst3`/`lv2`, `all` and `sums`."""
    urls = {}
    for asset in release.get("assets", []):
        name, url = asset["name"], asset["browser_download_url"]
        if name == "SHA256SUMS":
            urls["sums"] = url
            continue
        for fmt, _ in FORMATS:
            if name.endswith(f"-{fmt}.tar.gz"):
                urls[fmt] = url
                break
        else:
            if ALL_ASSET.search(name):
                urls["all"] = url
    return urls


def version_of(release):
    return release["tag_name"].partition("-v")[2]


def demo_link(name, base):
    return f"{base}demo/index.html?fx={name}"


def primary(release):
    """(label suffix, URL) of an effect's main download: the combined tarball, else CLAP."""
    urls = assets(release) if release else {}
    if urls.get("all"):
        return "", urls["all"]
    if urls.get("clap"):
        return " (CLAP)", urls["clap"]
    return None


def block(name, display, release, base="../"):
    """Markdown for one effect page."""
    main = primary(release)
    if not main:
        return (
            f'!!! note "Not released yet"\n'
            f"    {display} has no published release yet. You can "
            f"[play it in your browser]({demo_link(name, base)}) now, or "
            f"[build it from source]({base}install.md). Releases appear on the "
            f"[releases page]({RELEASES_PAGE}) when they are published.\n"
        )
    urls = assets(release)
    buttons = (
        f"[Download {display} {version_of(release)}{main[0]}]({main[1]})"
        "{ .md-button .md-button--primary }"
        f" [Try it in your browser]({demo_link(name, base)}){{ .md-button }}"
    )
    single = [f"[{label}]({urls[fmt]})" for fmt, label in FORMATS if urls.get(fmt)]
    also = f"Single formats: {' · '.join(single)}\n\n" if single and urls.get("all") else ""
    tail = (
        f"Linux x86_64. CLAP, VST3 and LV2 with an installer. {release_sums(release)}"
        f"[Release notes]({release['html_url']}) · [How to install]({base}download.md#install)"
    )
    return f"{buttons}\n\n{also}{tail}\n"


def button(name, display, release, base=""):
    """One download button for an effect card, or a browser-demo button if unreleased."""
    main = primary(release)
    if not main:
        return (
            f"[Play in your browser]({demo_link(name, base)}){{ .md-button }}\n\nNot released yet."
        )
    label, url = main
    return f"[Download {version_of(release)}{label}]({url}){{ .md-button .md-button--primary }}"


def release_sums(release):
    url = assets(release).get("sums")
    return f"[SHA256SUMS]({url}) · " if url else ""


def table(effects, latest, base=""):
    """Markdown table of every effect: what it is, version, download and browser demo.

    `effects` is (name, display name, description) per effect. The download
    cell links the combined tarball, then any single-format archives.
    """
    rows = ["| Effect | Version | Download | Try it |", "|---|---|---|---|"]
    for name, display, description in effects:
        release = latest.get(name)
        urls = assets(release) if release else {}
        found = []
        if urls.get("all"):
            found.append(f"**[All formats]({urls['all']})**")
        found += [f"[{label}]({urls[fmt]})" for fmt, label in FORMATS if urls.get(fmt)]
        download = " · ".join(found) or "not released yet"
        version = version_of(release) if release else "–"
        effect = f"**[{display}]({base}{name}/index.md)**<br>{description}"
        demo = f"[Play in your browser]({demo_link(name, base)})"
        rows.append(f"| {effect} | {version} | {download} | {demo} |")
    note = (
        "Linux x86_64. Each download holds CLAP, VST3 and LV2 plugins and an installer. "
        f"Older versions and checksums are on the [releases page]({RELEASES_PAGE}).\n"
    )
    return "\n".join(rows) + "\n\n" + note
