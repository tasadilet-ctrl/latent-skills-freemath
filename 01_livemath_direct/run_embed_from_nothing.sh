#!/usr/bin/env bash
# LiveMath -- EMBEDDING SKILL, extracted against NO system message.
#
#   ./run_embed_from_nothing.sh <vectors.pt> <layers> <gamma>
#
# Arm B2. The vector is
#     mean activations under [skill]  -  mean under [no system message at all]
#
# UNCONTROLLED BY CONSTRUCTION. The contrast contains both "the procedure" and
# "there is instructional text in the system slot", and nothing separates
# them. It is in the matrix precisely so it can be compared against the
# placebo-controlled arm -- the difference between the two is the study's main
# finding, not a bug. Do not report this arm on its own as "the embedding
# skill works".
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_EVAL" eval
VEC="${1:?usage: ./run_embed_from_nothing.sh <vectors.pt> <layers> <gamma>}"
LAYERS="${2:?need layers}"; GAMMA="${3:?need gamma}"
[ -f "$VEC" ] || VEC="$VECTORS/$(basename "$VEC")"
[ -f "$VEC" ] || fail "no such vector: $VEC"
note "vector $(basename "$VEC")  layers=$LAYERS gamma=$GAMMA"
submit "livemath_${MODEL_TAG}_embed_none" "$PY_EVAL" "$KIT/src/evaluate.py" \
  --domain livemath --condition embed --vectors "$VEC" \
  --layers "$LAYERS" --gamma "$GAMMA" --mode relative \
  --limit "$LIMIT" --batch-size "$BS" --max-new-tokens "$MAXNEW"
