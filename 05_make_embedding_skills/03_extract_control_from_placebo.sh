#!/usr/bin/env bash
# STEP 1c -- build the CONTROL vector: source skill = the placebo itself.
#
#   ./03_extract_control_from_placebo.sh
#
# The placebo is text shaped like a procedure that contains no procedure. A
# vector built FROM it should carry nothing. If steering with it still moves
# the benchmark, then the method transports "instructional text was present"
# and not the skill -- which is exactly what the LiveMath results showed.
#
# This cell is what makes the embedding numbers interpretable. Without it,
# a positive embed result has no null to be measured against.
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_EVAL" eval
PL="$(skill_path "${PLACEBO:-$SKILL_PLACEBO}")"
[ -f "$PL" ] || fail "no such placebo: $PL"
say "extracting CONTROL from $(basename "$PL")   [$MODEL_TAG]"
NO_SHARD=1 SHARDS=1 submit "extract_control_${MODEL_TAG}" "$PY_EVAL" \
  "$KIT/src/extract_vectors.py" \
  --pool "${POOL:-neutral}" --n "${NPOOL:-50}" --skill "$PL"
