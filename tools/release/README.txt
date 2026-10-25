SPDX-FileCopyrightText: 2026 Joe Heffer
SPDX-License-Identifier: MIT

A pedalkit effect as LV2, VST3 and CLAP plugins for Linux (x86_64)
==================================================================

Install for the current user (no root needed):

    ./install.sh

This copies the plugins into ~/.lv2, ~/.vst3 and ~/.clap, the folders that
REAPER, Bitwig, Ardour, Carla and other Linux hosts scan. Then rescan plugins
in your DAW. Options:

    ./install.sh --lv2 --clap    install only some formats
    ./install.sh --uninstall     remove them again
    ./install.sh --help

Requires glibc 2.35 or newer (Ubuntu 22.04, Debian 12 or later, or any
current rolling distribution).

CHANGELOG.md lists what changed in each version of this effect. Its
controls, measurements and known limitations are documented at
https://joe-heffer.github.io/faust-pedalkit/
Source code and issues: https://github.com/Joe-Heffer/faust-pedalkit
