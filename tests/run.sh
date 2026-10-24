#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
# Run every tests/<effect>/test_*.py for one effect.
# Usage: tests/run.sh <effect>      (the Makefile's `test` target calls this)
# Exits non-zero if any test fails. Plots and WAVs go to tests/out/<effect>/.
set -u
fx=${1:?usage: tests/run.sh <effect>}
here=$(cd "$(dirname "$0")" && pwd)

if ! compgen -G "$here/$fx/test_*.py" >/dev/null; then
    echo "no tests in tests/$fx/"
    exit 1
fi

status=0
for t in "$here/$fx"/test_*.py; do
    FX=$fx PYTHONPATH="$here/lib" python3 "$t" || status=1
    echo
done
echo "plots and WAV renders are in tests/out/$fx/"
exit $status
