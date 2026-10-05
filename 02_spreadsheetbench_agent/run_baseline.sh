#!/usr/bin/env bash
# SpreadsheetBench (AGENT) -- BASELINE. Mechanics prompt only, no skill.
#
#   ./run_baseline.sh
#   LIMIT=20 ./run_baseline.sh         # smoke test first. Always.
#
# NEEDS A SERVED MODEL. The agent talks HTTP; it does not load weights.
# Start one first:   ../00_setup/05_serve_model.sh plain
#
# The agent gets a shell and a file editor and a workspace holding input.xlsx,
# and must leave output.xlsx behind. Grading compares the task's answer range
# against the golden workbook.
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_AGENT" agent
require_data "$DATA/spreadsheetbench_verified_400"
require_served_model
SHARDS="${SHARDS:-4}"
submit "sb_agent_${MODEL_TAG}_baseline" "$PY_AGENT" "$KIT/src/run_sb_agent.py" \
  --condition baseline --limit "${LIMIT_SB:-400}" \
  --max-iterations "${MAX_ITER:-15}" --location-hint off
