#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
# Run every tests/<effect>/test_*.py for one effect, then the checks in
# tests/common/ that every effect gets without writing them: latency report,
# zipper noise on every control, CPU use and recovery after a hot input.
# Usage: tests/run.sh [--no-cpu] <effect>
# Exits non-zero if any test fails. Plots and WAVs go to tests/out/<effect>/.
# --no-cpu leaves out tests/common/test_cpu.py. `make test` uses it to run the
# effects in parallel, then times every effect's CPU use on its own afterwards,
# so that the timings aren't skewed by the other effects' tests.
set -u
skip_cpu=
if [ "${1:-}" = --no-cpu ]; then
    skip_cpu=1
    shift
fi
fx=${1:?usage: tests/run.sh [--no-cpu] <effect>}
here=$(cd "$(dirname "$0")" && pwd)

if ! compgen -G "$here/$fx/test_*.py" >/dev/null; then
    echo "no tests in tests/$fx/"
    exit 1
fi

status=0
for t in "$here/$fx"/test_*.py "$here"/common/test_*.py; do
    if [ -n "$skip_cpu" ] && [ "$(basename "$t")" = test_cpu.py ]; then
        continue
    fi
    FX=$fx PYTHONPATH="$here/lib" python3 "$t" || status=1
    echo
done
echo "plots and WAV renders are in tests/out/$fx/"
exit $status
