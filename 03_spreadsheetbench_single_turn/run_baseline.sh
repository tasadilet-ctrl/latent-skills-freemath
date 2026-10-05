#!/usr/bin/env bash
# SpreadsheetBench (SINGLE-TURN) -- BASELINE.
#
#   ./run_baseline.sh
#
# NO SERVED MODEL NEEDED: this arm runs the model IN-PROCESS with batching.
# That is the whole reason it exists -- the embedding arm costs ~1 h here
# against ~25 h through the serial hooked server that the agent arm requires.
#
# The model sees a rendering of the workbook and emits the edit in one turn.
# It is a weaker task than the agent arm (no tools, no iteration), so its
# scores are LOWER and are not comparable to the agent rows. It is a separate
# row in the matrix, not a cheaper version of the same cell.
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_EVAL" eval
require_data "$DATA/spreadsheetbench_verified_400"
submit "sb_single_${MODEL_TAG}_baseline" "$PY_EVAL" "$KIT/src/evaluate_spreadsheet.py" \
  --condition baseline --limit "${LIMIT_SB:-400}" \
  --batch-size "${BS_SB:-4}" --max-new-tokens "${MAXNEW_SB:-1536}"
