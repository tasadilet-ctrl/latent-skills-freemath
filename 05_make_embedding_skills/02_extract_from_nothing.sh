#!/usr/bin/env bash
# STEP 1b -- build the UNCONTROLLED vector (arm B2).
#
#   ./02_extract_from_nothing.sh
#
#     v = mean activations under [skill]  -  mean under [no system message]
#
# The contrast now contains the procedure AND the bare presence of
# instructional text, with nothing separating them. That is deliberate: B1 vs
# B2 is the comparison the study is built on. Build both.
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_EVAL" eval
SK="$(skill_path "${SKILL:-$SKILL_LIVEMATH}")"
[ -f "$SK" ] || fail "no such skill: $SK"
say "extracting $(basename "$SK")  vs  nothing   [$MODEL_TAG]"
SHARDS=1 submit "extract_none_${MODEL_TAG}" "$PY_EVAL" \
  "$KIT/src/extract_vectors.py" \
  --pool "${POOL:-neutral}" --n "${NPOOL:-50}" --skill "$SK"
note "writes ../vectors/v_${MODEL_TAG}_<skill>.pt"
