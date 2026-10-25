#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Build the factory presets in src/<effect>.presets.toml into each plug-in
format.

Usage:
  presets.py lv2    <effect.presets.toml> <controls.json> <bundle> <plugin URI>
  presets.py header <effect.presets.toml or -> <controls.json> <out/presets.h>

The TOML file holds a list of [[preset]] tables, each with a `name`, an
optional `comment` and a `controls` table keyed by UI label (as in the test
scripts, e.g. Drive = 65). <controls.json> is the effect's `faust -json`
description, which lists the input controls in the order buildUserInterface()
reports them, so in the VST3 and CLAP parameter order. Every input control
must be set and lie within its range, otherwise this script fails rather than
writing a preset that depends on whatever the host had loaded before. The
same checks apply to every format.

lv2: writes <bundle>/presets.ttl and appends one pset:Preset entry per preset
to <bundle>/manifest.ttl, so hosts list the presets without loading the
plug-in. Labels are mapped to LV2 port symbols by reading the bundle's own
<effect>.ttl, since faust2lv2 derives the symbols from the labels and the port
order.

header: writes presets.h for the VST3 and CLAP architectures
(tools/vst3/faust-vst3.cpp, tools/clap/faust-clap.cpp): each preset's name,
comment and value for every control, in parameter order. With `-` in place of
the TOML file (an effect without presets) it writes an empty table, so the
architectures build the same way for every effect.
"""

import json
import os
import re
import sys
import tomllib

INPUTS = {"hslider", "vslider", "nentry", "checkbox", "button"}


def controls(json_path):
    """The effect's input controls in parameter order: [(label, min, max)]."""
    out = []

    def walk(items):
        for item in items:
            if "items" in item:
                walk(item["items"])
            elif item["type"] in INPUTS:
                if item["type"] in ("checkbox", "button"):
                    out.append((item["label"], 0.0, 1.0))
                else:
                    out.append((item["label"], float(item["min"]), float(item["max"])))

    walk(json.load(open(json_path))["ui"])
    return out


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def quote(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def load(toml_path, ctrls):
    """The presets, each with its values in parameter order. Exits on any
    unknown, missing or out-of-range control, or a duplicate name."""
    presets = tomllib.load(open(toml_path, "rb")).get("preset", [])
    labels = {label for label, _, _ in ctrls}
    errors, seen = [], set()
    for p in presets:
        name, given = p["name"], p.get("controls", {})
        if slug(name) in seen:
            errors.append(f"{name}: duplicate preset name")
        seen.add(slug(name))
        for label in given.keys() - labels:
            errors.append(f"{name}: no input control labelled {label!r}")
        values = []
        for label, lo, hi in ctrls:
            if label not in given:
                errors.append(f"{name}: control {label!r} is not set")
                continue
            v = float(given[label])
            if not lo <= v <= hi:
                errors.append(f"{name}: {label} = {v:g} is outside {lo:g} to {hi:g}")
            values.append(v)
        p["values"] = values
    if errors:
        sys.exit(f"{toml_path}:\n  " + "\n  ".join(errors))
    return presets


def lv2(toml_path, json_path, bundle, uri):
    ctrls = controls(json_path)
    presets = load(toml_path, ctrls)
    effect = os.path.basename(bundle.rstrip("/")).removesuffix(".lv2")
    ttl = open(os.path.join(bundle, f"{effect}.ttl")).read()

    # Input control ports: label -> symbol.
    symbols = {}
    for block in re.split(r"lv2:port\b(?!Property)|\] , \[", ttl)[1:]:
        if "lv2:InputPort" not in block or "lv2:ControlPort" not in block:
            continue
        field = dict(re.findall(r'lv2:(symbol|name) "?([^";\n]*)"?\s*;', block))
        symbols[field["name"]] = field["symbol"]
    missing = [label for label, _, _ in ctrls if label not in symbols]
    if missing:
        sys.exit(f"{bundle}: no LV2 port for {', '.join(missing)}")

    body, manifest = [], []
    for p in presets:
        puri = f"{uri}/preset/{slug(p['name'])}"
        values = [
            f"[ lv2:symbol {quote(symbols[label])} ; pset:value {v!r} ]"
            for (label, _, _), v in zip(ctrls, p["values"], strict=True)
        ]
        lines = [
            f"<{puri}>",
            "    a pset:Preset ;",
            f"    lv2:appliesTo <{uri}> ;",
            f"    rdfs:label {quote(p['name'])} ;",
        ]
        if "comment" in p:
            lines.append(f"    rdfs:comment {quote(p['comment'])} ;")
        lines.append("    lv2:port\n        " + " ,\n        ".join(values) + " .")
        body.append("\n".join(lines))
        manifest.append(
            f"<{puri}>\n    a pset:Preset ;\n    lv2:appliesTo <{uri}> ;\n"
            "    rdfs:seeAlso <presets.ttl> ."
        )

    prefixes = (
        "@prefix lv2:  <http://lv2plug.in/ns/lv2core#> .\n"
        "@prefix pset: <http://lv2plug.in/ns/ext/presets#> .\n"
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
    )
    with open(os.path.join(bundle, "presets.ttl"), "w") as f:
        f.write(f"# Generated from {os.path.basename(toml_path)} by tools/presets.py.\n\n")
        f.write(prefixes + "\n" + "\n\n".join(body) + "\n")
    with open(os.path.join(bundle, "manifest.ttl"), "a") as f:
        f.write("\n# Factory presets (tools/presets.py).\n\n")
        f.write(prefixes + "\n" + "\n\n".join(manifest) + "\n")
    print(f"{bundle}: {len(presets)} preset(s)")


def header(toml_path, json_path, out_path):
    ctrls = controls(json_path)
    presets = [] if toml_path == "-" else load(toml_path, ctrls)
    source = "no presets file" if toml_path == "-" else toml_path
    lines = [
        f"// Generated by tools/presets.py from {source}. Do not edit.",
        "#pragma once",
        "",
        "// Controls in parameter order: "
        + (", ".join(label for label, _, _ in ctrls) or "none")
        + ".",
        f"static constexpr unsigned kNumPresetControls = {len(ctrls)};",
        f"static constexpr unsigned kNumPresets = {len(presets)};",
        "",
        "struct FxPreset {",
        "    const char* name;",
        "    const char* comment;",
        "    float values[kNumPresetControls > 0 ? kNumPresetControls : 1];",
        "};",
        "",
    ]
    if presets:
        lines.append("static const FxPreset kPresets[kNumPresets] = {")
        for p in presets:
            values = ", ".join(f"{v!r}f" for v in p["values"])
            comment = quote(p.get("comment", ""))
            lines.append(f"    {{{quote(p['name'])}, {comment}, {{{values}}}}},")
        lines.append("};")
    else:
        lines.append("static const FxPreset* const kPresets = nullptr;")
    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    commands = {"lv2": (lv2, 4), "header": (header, 3)}
    if (
        len(sys.argv) < 2
        or sys.argv[1] not in commands
        or len(sys.argv) != commands[sys.argv[1]][1] + 2
    ):
        sys.exit(__doc__)
    fn, _ = commands[sys.argv[1]]
    fn(*sys.argv[2:])
