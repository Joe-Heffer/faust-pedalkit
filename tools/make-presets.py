#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Add factory presets from src/<effect>.presets.toml to an LV2 bundle.

Usage: make-presets.py <effect.presets.toml> <bundle> <plugin URI>

The TOML file holds a list of [[preset]] tables, each with a `name`, an
optional `comment` and a `controls` table keyed by UI label (as in the test
scripts, e.g. Drive = 65). Labels are mapped to LV2 port symbols by reading
the bundle's own <effect>.ttl, since faust2lv2 derives the symbols from the
labels and the port order. Every input control must be set and lie within its
range, otherwise this script fails rather than writing a preset that depends
on whatever the host had loaded before.

Writes <bundle>/presets.ttl and appends one pset:Preset entry per preset to
<bundle>/manifest.ttl, so hosts list the presets without loading the plugin.
"""

import os
import re
import sys
import tomllib

toml_path, bundle, uri = sys.argv[1], sys.argv[2], sys.argv[3]
effect = os.path.basename(bundle.rstrip("/")).removesuffix(".lv2")
presets = tomllib.load(open(toml_path, "rb")).get("preset", [])
ttl = open(os.path.join(bundle, f"{effect}.ttl")).read()

# Input control ports: label -> (symbol, minimum, maximum).
ports = {}
for block in re.split(r"lv2:port\b(?!Property)|\] , \[", ttl)[1:]:
    if "lv2:InputPort" not in block or "lv2:ControlPort" not in block:
        continue
    field = {
        k: v for k, v in re.findall(r'lv2:(symbol|name|minimum|maximum) "?([^";\n]*)"?\s*;', block)
    }
    ports[field["name"]] = (field["symbol"], float(field["minimum"]), float(field["maximum"]))


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def quote(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


errors = []
body, manifest = [], []
seen = set()
for p in presets:
    name, controls = p["name"], p.get("controls", {})
    puri = f"{uri}/preset/{slug(name)}"
    if puri in seen:
        errors.append(f"{name}: duplicate preset name")
    seen.add(puri)
    for label in controls.keys() - ports.keys():
        errors.append(f"{name}: no input control labelled {label!r}")
    for label in ports.keys() - controls.keys():
        errors.append(f"{name}: control {label!r} is not set")
    values = []
    for label, (symbol, lo, hi) in ports.items():
        if label not in controls:
            continue
        v = float(controls[label])
        if not lo <= v <= hi:
            errors.append(f"{name}: {label} = {v:g} is outside {lo:g} to {hi:g}")
        values.append(f"[ lv2:symbol {quote(symbol)} ; pset:value {v!r} ]")

    lines = [
        f"<{puri}>",
        "    a pset:Preset ;",
        f"    lv2:appliesTo <{uri}> ;",
        f"    rdfs:label {quote(name)} ;",
    ]
    if "comment" in p:
        lines.append(f"    rdfs:comment {quote(p['comment'])} ;")
    lines.append("    lv2:port\n        " + " ,\n        ".join(values) + " .")
    body.append("\n".join(lines))
    manifest.append(
        f"<{puri}>\n    a pset:Preset ;\n    lv2:appliesTo <{uri}> ;\n"
        "    rdfs:seeAlso <presets.ttl> ."
    )

if errors:
    sys.exit(f"{toml_path}:\n  " + "\n  ".join(errors))

prefixes = (
    "@prefix lv2:  <http://lv2plug.in/ns/lv2core#> .\n"
    "@prefix pset: <http://lv2plug.in/ns/ext/presets#> .\n"
    "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
)
with open(os.path.join(bundle, "presets.ttl"), "w") as f:
    f.write(f"# Generated from {os.path.basename(toml_path)} by tools/make-presets.py.\n\n")
    f.write(prefixes + "\n" + "\n\n".join(body) + "\n")
with open(os.path.join(bundle, "manifest.ttl"), "a") as f:
    f.write("\n# Factory presets (tools/make-presets.py).\n\n")
    f.write(prefixes + "\n" + "\n\n".join(manifest) + "\n")
print(f"{bundle}: {len(presets)} preset(s)")
