#!/usr/bin/env bash
# SpreadsheetBench (SINGLE-TURN) -- EMBEDDING SKILL from a NO-MESSAGE contrast (B2, UNCONTROLLED)
#
#   ./run_embed_from_nothing.sh <vectors.pt> <layers> <gamma>
#
# vector = E[h | skill] - E[h | no system message]. Holds the procedure AND
# the presence of instructional text, inseparably. Exists for the comparison
# against B1; never report it on its own.
#
# NO SERVER NEEDED. This arm loads weights in-process and applies the hooks
# directly, with batching -- which is the whole reason it exists: the same
# vector costs ~1 h here against ~25 h through the serial hooked server the
# agent arm requires.
#
# It is a SEPARATE ROW from the agent arm, not a cheaper substitute: no shell,
# no iteration, so scores are strictly lower and are not comparable.
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_EVAL" eval
require_data "$DATA/spreadsheetbench_verified_400"
VEC="${1:?usage: ./run_embed_from_nothing.sh <vectors.pt> <layers> <gamma>}"
LAYERS="${2:?need layers}"; GAMMA="${3:?need gamma}"
[ -f "$VEC" ] || VEC="$VECTORS/$(basename "$VEC")"
[ -f "$VEC" ] || fail "no such vector: $VEC  (build one in ../05_make_embedding_skills/)"
note "vector $(basename "$VEC")  layers=$LAYERS gamma=$GAMMA"
submit "sb_single_${MODEL_TAG}_embed_from_nothing" "$PY_EVAL" "$KIT/src/evaluate_spreadsheet.py" \
  --condition embed --vectors "$VEC" --layers "$LAYERS" --gamma "$GAMMA" \
  --mode relative --limit "${LIMIT_SB:-400}" \
  --batch-size "${BS_SB:-4}" --max-new-tokens "${MAXNEW_SB:-1536}"
