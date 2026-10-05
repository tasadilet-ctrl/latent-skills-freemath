#!/usr/bin/env bash
# SpreadsheetBench (SINGLE-TURN) -- TEXT SKILL as system prompt.
#
#   ./run_text_skill.sh
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_EVAL" eval
require_data "$DATA/spreadsheetbench_verified_400"
SK="$(skill_path "$SKILL_SPREADSHEET")"
[ -f "$SK" ] || fail "no such skill: $SK"
submit "sb_single_${MODEL_TAG}_text" "$PY_EVAL" "$KIT/src/evaluate_spreadsheet.py" \
  --condition text --skill "$SK" --limit "${LIMIT_SB:-400}" \
  --batch-size "${BS_SB:-4}" --max-new-tokens "${MAXNEW_SB:-1536}"
