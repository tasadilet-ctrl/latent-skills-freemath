#!/usr/bin/env bash
# OfficeQA (AGENT) -- TEXT SKILL appended to the mechanics prompt.
#
#   ./run_text_skill.sh
#
# NEEDS A SERVED MODEL:   ../00_setup/05_serve_model.sh plain
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_AGENT" agent
require_data "$DATA/officeqa_docs"
require_served_model
SK="$(skill_path "$SKILL_OFFICEQA")"
[ -f "$SK" ] || fail "no such skill: $SK"
note "skill: $(basename "$SK")"
submit "oqa_${MODEL_TAG}_text" "$PY_AGENT" "$KIT/src/run_oqa_agent.py" \
  --condition text --skill "$SK" --limit "${LIMIT_OQA:-239}" \
  --max-iterations "${MAX_ITER:-25}"
