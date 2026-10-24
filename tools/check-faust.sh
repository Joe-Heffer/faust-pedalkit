#!/usr/bin/env bash
# Compile every src/*.dsp to /dev/null so syntax and type errors are caught
# before commit. Used by the faust-compile pre-commit hook.
set -u
root=$(cd "$(dirname "$0")/.." && pwd)
status=0
for dsp in "$root"/src/*.dsp; do
    faust -I "$root/src/lib" "$dsp" -o /dev/null || { echo "faust: $dsp failed"; status=1; }
done
exit $status
