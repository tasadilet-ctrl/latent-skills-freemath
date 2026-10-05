#!/usr/bin/env bash
# SpreadsheetBench (AGENT) -- TEXT SKILL appended to the mechanics prompt.
#
#   ./run_text_skill.sh
#
# NEEDS A SERVED MODEL:   ../00_setup/05_serve_model.sh plain
#
# The mechanics prompt (tools, stopping condition) is byte-identical to the
# baseline arm; the skill is appended to it. So the two arms differ by the
# skill and nothing else -- which is the only reason the difference means
# anything.
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_AGENT" agent
require_data "$DATA/spreadsheetbench_verified_400"
require_served_model
SK="$(skill_path "$SKILL_SPREADSHEET")"
[ -f "$SK" ] || fail "no such skill: $SK"
note "skill: $(basename "$SK")"
submit "sb_agent_${MODEL_TAG}_text" "$PY_AGENT" "$KIT/src/run_sb_agent.py" \
  --condition text --skill "$SK" --limit "${LIMIT_SB:-400}" \
  --max-iterations "${MAX_ITER:-15}" --location-hint off
