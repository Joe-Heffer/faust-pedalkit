#!/bin/sh
# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
#
# Checks that every plugin binary in an unpacked release links on this
# system: no missing libraries and no missing glibc or libstdc++ symbol
# versions. The release workflow runs it in the oldest distribution we
# support (Ubuntu 22.04). For each binary it also prints the newest glibc
# and libstdc++ symbol versions it needs.
#
#   tools/release/check-portable.sh <unpacked release folder>

set -eu

dir=${1:?usage: check-portable.sh <unpacked release folder>}
status=0
found=0
for so in $(find "$dir" -name '*.so' -o -name '*.clap' | sort); do
    found=$((found + 1))
    out=$(ldd -r "$so" 2>&1) || true
    needs=$(grep -ao 'GLIBC_[0-9.]*\|GLIBCXX_[0-9.]*' "$so" | sort -u -V |
        awk -F_ '{v[$1] = $0} END {printf "%s %s", v["GLIBC"], v["GLIBCXX"]}')
    if printf '%s\n' "$out" | grep -E 'not found|undefined symbol' >/dev/null; then
        echo "FAIL $so ($needs)"
        printf '%s\n' "$out" | sed 's/^/    /'
        status=1
    else
        echo "ok   $so ($needs)"
    fi
done
[ "$found" -gt 0 ] || { echo "check-portable.sh: no plugin binaries under $dir" >&2; exit 1; }
exit $status
