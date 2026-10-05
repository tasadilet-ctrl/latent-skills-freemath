#!/usr/bin/env bash
# SpreadsheetBench (SINGLE-TURN) -- EMBEDDING SKILL.
#
#   ./run_embed.sh <vectors.pt> <layers> <gamma>
#
# This is the ONLY practical way to get a SpreadsheetBench embed cell. The
# agent arm would need the serial hooked server (~25 h); here steering is
# applied in-process with batching (~1 h).
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_EVAL" eval
require_data "$DATA/spreadsheetbench_verified_400"
VEC="${1:?usage: ./run_embed.sh <vectors.pt> <layers> <gamma>}"
LAYERS="${2:?need layers}"; GAMMA="${3:?need gamma}"
[ -f "$VEC" ] || VEC="$VECTORS/$(basename "$VEC")"
[ -f "$VEC" ] || fail "no such vector: $VEC"
submit "sb_single_${MODEL_TAG}_embed" "$PY_EVAL" "$KIT/src/evaluate_spreadsheet.py" \
  --condition embed --vectors "$VEC" --layers "$LAYERS" --gamma "$GAMMA" \
  --mode relative --limit "${LIMIT_SB:-400}" \
  --batch-size "${BS_SB:-4}" --max-new-tokens "${MAXNEW_SB:-1536}"
