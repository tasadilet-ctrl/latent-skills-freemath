#!/usr/bin/env bash
# Render the matrix as a PNG table -> ../results_table.png
#
#   ./table_png.sh
#
# Runs in the isolated plotting venv: a matplotlib numpy and a torch numpy
# routinely disagree, and this keeps the eval environment out of it.
#
# A table, not a chart -- the data is a small grid of labelled values readers
# need to look up exactly. Colour carries one thing only: the sign of the
# change against that row's own baseline. Significance is text (bold + *),
# never colour alone.
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_PLOT" plot
"$PY_PLOT" "$KIT/src/make_table_png.py" "$@"
