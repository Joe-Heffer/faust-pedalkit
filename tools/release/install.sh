#!/bin/sh
# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
#
# Installs the plugins in this release into the per-user plugin folders that
# Linux DAWs scan: ~/.lv2, ~/.vst3 and ~/.clap. Needs no root. It only ever
# touches the bundles that ship next to it, replacing older copies of them.
#
#   ./install.sh                 install every format
#   ./install.sh --lv2 --clap    install only these formats
#   ./install.sh --uninstall     remove them again (with or without format flags)
#
# LV2DIR, VST3DIR and CLAPDIR override the target folders, as in the Makefile.

set -eu

here=$(cd "$(dirname "$0")" && pwd)
LV2DIR=${LV2DIR:-$HOME/.lv2}
VST3DIR=${VST3DIR:-$HOME/.vst3}
CLAPDIR=${CLAPDIR:-$HOME/.clap}

usage() {
    sed -n 's/^#   \(\.\/install\.sh\)/\1/p' "$0"
    echo
    echo "Targets: LV2 $LV2DIR, VST3 $VST3DIR, CLAP $CLAPDIR"
}

action=install
formats=
for arg in "$@"; do
    case $arg in
        --lv2) formats="$formats lv2" ;;
        --vst3) formats="$formats vst3" ;;
        --clap) formats="$formats clap" ;;
        --uninstall) action=uninstall ;;
        -h | --help) usage; exit 0 ;;
        *) echo "install.sh: unknown option '$arg'" >&2; usage >&2; exit 2 ;;
    esac
done
[ -n "$formats" ] || formats="lv2 vst3 clap"

target_dir() {
    case $1 in
        lv2) echo "$LV2DIR" ;;
        vst3) echo "$VST3DIR" ;;
        clap) echo "$CLAPDIR" ;;
    esac
}

count=0
for fmt in $formats; do
    src=$here/$fmt
    dest=$(target_dir "$fmt")
    [ -d "$src" ] || { echo "install.sh: $src is missing" >&2; exit 1; }
    for item in "$src"/*; do
        [ -e "$item" ] || continue
        name=$(basename "$item")
        if [ "$action" = install ]; then
            mkdir -p "$dest"
            rm -rf "${dest:?}/$name"
            cp -R "$item" "$dest/"
            echo "installed $dest/$name"
            count=$((count + 1))
        elif [ -e "$dest/$name" ]; then
            rm -rf "${dest:?}/$name"
            echo "removed $dest/$name"
            count=$((count + 1))
        fi
    done
done

if [ "$action" = install ]; then
    echo "Installed $count plugin(s). Rescan plugins in your DAW to pick them up."
else
    echo "Removed $count plugin(s)."
fi
