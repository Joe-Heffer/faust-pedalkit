#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Fill in LV2 metadata that faust2lv2 cannot express, so lv2lint passes.

Usage: fix-ttl.py <effect.dsp> <bundle>/<effect>.ttl

Reads these global declarations from the Faust source:

  declare license  "MIT";              SPDX identifier -> doap:license URI
  declare version  "0.1.0";            -> lv2:minorVersion / lv2:microVersion
  declare lv2class "DistortionPlugin"; -> a lv2:DistortionPlugin (plugin class)
  declare homepage "https://...";      -> foaf:homepage on the maintainer (optional)

The TTL is edited in place.
"""

import re
import sys

from dspmeta import declares

dsp_path, ttl_path = sys.argv[1], sys.argv[2]
decl = declares(dsp_path)
ttl = open(ttl_path).read()

# The plugin's own triples start at its subject and end at the first port.
head, sep, rest = ttl.partition("    lv2:port")
if not sep:
    sys.exit(f"{ttl_path}: no lv2:port found, unexpected faust2lv2 output")

if "license" in decl:
    head = re.sub(
        r'doap:license "[^"]*"', f"doap:license <https://spdx.org/licenses/{decl['license']}>", head
    )

extra = []
if "version" in decl:
    m = re.fullmatch(r"(\d+)\.(\d+)(?:\.(\d+))?", decl["version"])
    if not m:
        sys.exit(f'version "{decl["version"]}" must look like major.minor.micro')
    extra += [f"lv2:minorVersion {int(m.group(2))}", f"lv2:microVersion {int(m.group(3) or 0)}"]
if "lv2class" in decl:
    head = head.replace("a lv2:Plugin ;", f"a lv2:Plugin, lv2:{decl['lv2class']} ;", 1)
if "homepage" in decl:
    head = re.sub(
        r'doap:maintainer \[ foaf:name "([^"]*)" \]',
        rf'doap:maintainer [ foaf:name "\1" ; foaf:homepage <{decl["homepage"]}> ]',
        head,
    )

if extra:
    head = head.rstrip("\n") + "\n" + "".join(f"       {e} ;\n" for e in extra)

open(ttl_path, "w").write(head + sep + rest)
