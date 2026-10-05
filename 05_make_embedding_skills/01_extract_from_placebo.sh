#!/usr/bin/env bash
# STEP 1a -- build the CONTROLLED vector (arm B1).
#
#   ./01_extract_from_placebo.sh                           # LiveMath skill
#   SKILL=spreadsheet_edit.md POOL=spreadsheet ./01_extract_from_placebo.sh
#
# Takes a .md skill file and returns one direction per layer:
#
#     v = mean activations under [placebo + skill]  -  mean under [placebo]
#
# Both sides carry the length-matched placebo, so "a system prompt exists"
# cancels and what remains is meant to be the procedure itself.
#
# Activations are read at the FINAL PROMPT TOKEN over a pool of neutral tasks
# -- not the benchmark's own questions, or the vector memorises the benchmark
# instead of carrying a skill.
#
# Several placebos can be passed; their activations are averaged before
# subtraction, which keeps any single placebo's quirks out of the direction.
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_EVAL" eval
SK="$(skill_path "${SKILL:-$SKILL_LIVEMATH}")"
PL="$(skill_path "${PLACEBO:-$SKILL_PLACEBO}")"
[ -f "$SK" ] || fail "no such skill: $SK"
[ -f "$PL" ] || fail "no such placebo: $PL"
say "extracting $(basename "$SK")  vs  $(basename "$PL")   [$MODEL_TAG]"
RUNNER="${RUNNER}" SHARDS=1 submit "extract_placebo_${MODEL_TAG}" "$PY_EVAL" \
  "$KIT/src/extract_vectors.py" \
  --pool "${POOL:-neutral}" --n "${NPOOL:-50}" \
  --skill "$SK" --baseline-skill "$PL"
note "writes ../vectors/v_${MODEL_TAG}_<skill>_placebo.pt"
note "next: ./03_measure_fidelity.sh on it"
