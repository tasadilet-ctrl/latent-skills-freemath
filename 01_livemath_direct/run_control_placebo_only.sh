#!/usr/bin/env bash
# LiveMath -- CONTROL. A vector whose SOURCE SKILL is the placebo itself.
#
#   ./run_control_placebo_only.sh <vectors.pt> <layers> <gamma>
#
# The null arm. This vector was built from text that contains NO procedure --
# only the shape, length and register of one. If steering with it moves the
# score as much as steering with the real skill does, then what the method
# transports is "instructional text was present", not the procedure.
#
# This is the cell that makes the embedding result interpretable. Run it.
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_EVAL" eval
VEC="${1:?usage: ./run_control_placebo_only.sh <vectors.pt> <layers> <gamma>}"
LAYERS="${2:?need layers}"; GAMMA="${3:?need gamma}"
[ -f "$VEC" ] || VEC="$VECTORS/$(basename "$VEC")"
[ -f "$VEC" ] || fail "no such vector: $VEC"
case "$(basename "$VEC")" in *placebo_*|*_placebo*) : ;;
  *) warn "'$(basename "$VEC")' does not look like a placebo-sourced vector -- the CONTROL needs one built FROM the placebo." ;;
esac
submit "livemath_${MODEL_TAG}_control" "$PY_EVAL" "$KIT/src/evaluate.py" \
  --domain livemath --condition embed --vectors "$VEC" \
  --layers "$LAYERS" --gamma "$GAMMA" --mode relative \
  --limit "$LIMIT" --batch-size "$BS" --max-new-tokens "$MAXNEW"
