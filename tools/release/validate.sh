#!/bin/sh
# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
#
# Checks an unpacked release as a user would get it: install.sh installs it
# into temporary folders, lv2lint, pluginval and clap-validator run on the
# installed copies, and --uninstall must leave the folders empty. Runs in the
# toolchain image (Dockerfile), which has all three validators.
#
#   tools/release/validate.sh <unpacked release folder>

set -eu

rel=$(cd "${1:?usage: validate.sh <unpacked release folder>}" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
export LV2DIR="$work/lv2" VST3DIR="$work/vst3" CLAPDIR="$work/clap"

echo "== install.sh"
"$rel/install.sh"

status=0
for bundle in "$LV2DIR"/*.lv2; do
    name=$(basename "$bundle" .lv2)
    echo "== lv2lint $name"
    lv2lint -I "$bundle/" "urn:pedalkit/$name" || status=1
done
for bundle in "$VST3DIR"/*.vst3; do
    echo "== pluginval $(basename "$bundle")"
    pluginval --strictness-level 10 --skip-gui-tests --validate-in-process \
        --validate "$bundle" || status=1
done
# clap-validator's preset-discovery-crawl and -load tests deadlock on any
# container of two or more presets, so they are skipped as in `make
# clap-validate`, where tools/clap/check-presets.cpp covers the presets.
for plugin in "$CLAPDIR"/*.clap; do
    echo "== clap-validator $(basename "$plugin")"
    clap-validator validate --only-failed -x 'preset-discovery-(crawl|load)' "$plugin" || status=1
done

echo "== install.sh --uninstall"
"$rel/install.sh" --uninstall
left=$(find "$LV2DIR" "$VST3DIR" "$CLAPDIR" -mindepth 1 -maxdepth 1)
if [ -n "$left" ]; then
    echo "FAIL: --uninstall left:"
    echo "$left"
    status=1
fi
exit $status
