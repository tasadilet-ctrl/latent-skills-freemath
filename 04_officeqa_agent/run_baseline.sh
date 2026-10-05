#!/usr/bin/env bash
# OfficeQA (AGENT) -- BASELINE. Mechanics prompt only, no skill.
#
#   ./run_baseline.sh
#
# NEEDS A SERVED MODEL:   ../00_setup/05_serve_model.sh plain
#
# WHY THIS IS AN AGENT BENCHMARK AND NOT A PROMPT ONE
#   The bulletins one question references total ~215k tokens at the median,
#   534k at p90 and 1.2M at worst. Zero of the 246 questions fit an 8B/14B
#   context and only 58% fit the 27B. So the files go on disk and the agent
#   greps -- which is how the benchmark is meant to be used, and makes context
#   length irrelevant.
#
#   Only the files a question actually cites are linked into its workspace.
#   Exposing all 285 bulletins would turn this into corpus search, a different
#   and much harder task than the benchmark scores.
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_AGENT" agent
require_data "$DATA/officeqa_docs"
require_served_model
submit "oqa_${MODEL_TAG}_baseline" "$PY_AGENT" "$KIT/src/run_oqa_agent.py" \
  --condition baseline --limit "${LIMIT_OQA:-239}" \
  --max-iterations "${MAX_ITER:-25}"
