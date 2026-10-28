# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Download links for the website, from the repository's published releases.

Each effect is released on its own, under a tag `<name>-vX.Y.Z`. GitHub's
`releases/latest` is repo-wide, so it cannot name the latest release of one
effect. This finds, for each effect, the newest published (neither draft nor
pre-release) release and links its assets:

  <name>-<version>-linux-<arch>.tar.gz          all formats, with install.sh
  <name>-<version>-linux-<arch>-clap.tar.gz     one format each (clap, vst3, lv2)
  SHA256SUMS

tools/mkdocs_hooks.py swaps the markers `<!-- downloads:<name> -->` and
`<!-- downloads:all -->` in the pages for the Markdown made here. If no
release is published yet, or GitHub cannot be reached (an offline build), the
links point at the Releases page instead, so they never 404.
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


def links(release):
    """The links for one effect, CLAP first; the combined tarball stands in for a missing format."""
    if release is None:
        return None
    urls = assets(release)
    out = [(label, urls.get(fmt) or urls.get("all")) for fmt, label in FORMATS]
    out = [(label, url) for label, url in out if url]
    if urls.get("all"):
        out.append(("All formats + installer", urls["all"]))
    return out or None


def block(name, display, release):
    """Markdown for one effect page."""
    found = links(release)
    if not found:
        return (
            f'!!! note "Download"\n'
            f"    No release of {display} is published yet. Releases appear on the "
            f"[releases page]({RELEASES_PAGE}) when they are.\n"
        )
    first, *rest = found
    buttons = f"[Download {display} {version_of(release)} ({first[0]})]({first[1]}){{ .md-button .md-button--primary }}"
    others = " · ".join(f"[{label}]({url})" for label, url in rest)
    sums = release_sums(release)
    tail = f"Linux x86_64. {sums}[Release notes]({release['html_url']}) · [Install guide](../install.md#install-a-release)"
    return f"{buttons}\n\nAlso: {others}\n\n{tail}\n"


def release_sums(release):
    url = assets(release).get("sums")
    return f"[SHA256SUMS]({url}) · " if url else ""


def table(effects, latest):
    """Markdown table of every effect: name, version and one link per format."""
    rows = ["| Effect | Version | " + " | ".join(label for _, label in FORMATS) + " | All |", "|---|---|" + "---|" * (len(FORMATS) + 1)]
    for name, display in effects:
        release = latest.get(name)
        urls = assets(release) if release else {}
        cells = [f"[{label}]({urls.get(fmt) or urls.get('all')})" if urls.get(fmt) or urls.get("all") else "–" for fmt, label in FORMATS]
        everything = f"[tarball]({urls['all']})" if urls.get("all") else "–"
        version = version_of(release) if release else "not yet published"
        rows.append(f"| **{display}** | {version} | " + " | ".join(cells) + f" | {everything} |")
    return "\n".join(rows) + f"\n\nLinux x86_64 only. Older versions and checksums are on the [releases page]({RELEASES_PAGE}).\n"
