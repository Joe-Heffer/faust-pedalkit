# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
"""Read the global `declare key "value";` statements from a Faust source."""

import re


def declares(dsp_path):
    """Return the .dsp file's global declarations as a dict."""
    with open(dsp_path) as f:
        return dict(re.findall(r'^\s*declare\s+(\w+)\s+"([^"]*)"\s*;', f.read(), re.M))
