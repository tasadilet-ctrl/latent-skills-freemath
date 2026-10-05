#!/usr/bin/env bash
# LiveMath -- EMBEDDING SKILL, extracted against a PLACEBO system prompt.
#
#   ./run_embed_from_placebo.sh <vectors.pt> <layers> <gamma>
#   ./run_embed_from_placebo.sh v_qwen3-8b_compare_claims_placebo.pt 34 0.3
#
# Arm B1 of the matrix. The vector is
#     mean activations under [placebo + skill]  -  mean under [placebo alone]
# so the length-matched placebo text is present on BOTH sides and cancels.
# What survives is meant to be the procedure, not "a system prompt exists".
#
# THIS IS THE CONTROLLED ARM, and it is the one the study's conclusion rests
# on. Compare it with run_embed_from_nothing.sh: the uncontrolled arm carries
# most of the apparent effect, and subtracting a matched placebo removes it.
#
# Get the (layers, gamma) from 05_make_embedding_skills/ -- picking them by
# eye, or by whichever benchmark number looks best, is how you manufacture a
# result.
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_EVAL" eval
VEC="${1:?usage: ./run_embed_from_placebo.sh <vectors.pt> <layers> <gamma>}"
LAYERS="${2:?need layers, e.g. 34}"; GAMMA="${3:?need gamma, e.g. 0.3}"
[ -f "$VEC" ] || VEC="$VECTORS/$(basename "$VEC")"
[ -f "$VEC" ] || fail "no such vector: $VEC  (make one in 05_make_embedding_skills/)"
case "$(basename "$VEC")" in *placebo*) : ;;
  *) warn "'$(basename "$VEC")' does not look like a from-placebo vector." ;;
esac
note "vector $(basename "$VEC")  layers=$LAYERS gamma=$GAMMA"
submit "livemath_${MODEL_TAG}_embed_placebo" "$PY_EVAL" "$KIT/src/evaluate.py" \
  --domain livemath --condition embed --vectors "$VEC" \
  --layers "$LAYERS" --gamma "$GAMMA" --mode relative \
  --limit "$LIMIT" --batch-size "$BS" --max-new-tokens "$MAXNEW"
