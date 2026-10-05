#!/usr/bin/env bash
# STEP 3 -- make sure the chosen setting has not broken generation.
#
#   ./05_check_degeneration.sh <vectors.pt>
#
# WHY THIS STEP EXISTS AND IS NOT OPTIONAL
#   Fidelity is measured TEACHER-FORCED: it scores the next-token distribution
#   against a reference continuation. A vector can therefore score well on
#   fidelity while free generation has collapsed into repetition -- the
#   distribution looks right one token at a time and the actual output is
#   unusable.
#
#   This sweeps the same bands and gammas and reports a distinct-token ratio,
#   so a setting that degenerates is visible before it becomes a benchmark
#   cell that scores near zero for reasons nobody can see.
#
# Pick the operating point with the best FIDELITY among settings that PASS
# here. Not the best fidelity overall.
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_EVAL" eval
VEC="${1:?usage: ./05_check_degeneration.sh <vectors.pt>}"
[ -f "$VEC" ] || VEC="$VECTORS/$(basename "$VEC")"
[ -f "$VEC" ] || fail "no such vector: $VEC"
SHARDS=1 submit "calibrate_${MODEL_TAG}" "$PY_EVAL" "$KIT/src/calibrate.py" \
  --vectors "$VEC" --domain "${DOMAIN:-livemath}" --n "${NCAL:-32}" \
  --batch-size "${BS:-8}" --mode relative \
  --bands "${BANDS:-32,40,48,24-40,40-56}" \
  --gammas "${GAMMAS:-0.02,0.05,0.1,0.2,0.4}"
