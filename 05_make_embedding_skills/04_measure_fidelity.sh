#!/usr/bin/env bash
# STEP 2 -- find the (layer, gamma) at which a vector reproduces the skill.
#
#   ./04_measure_fidelity.sh <vectors.pt>
#   ./04_measure_fidelity.sh ../vectors/v_qwen3-8b_compare_claims_placebo.pt
#   PROBE=spreadsheet ./04_measure_fidelity.sh <vec>      # cross-domain
#
#     fidelity = 1 - KL(text || steered) / KL(text || plain)
#
#       1.0   steering reproduces the text skill exactly
#       0.0   steering achieves nothing the plain model did not already do
#       <0    steering moves AWAY from the skill
#
# WHY NOT JUST USE BENCHMARK ACCURACY TO PICK THE SETTINGS
#   If a skill is worth two points on a 608-item 5-way benchmark, accuracy
#   cannot tell "the vector works" from noise. Choosing layer and gamma by
#   whichever accuracy came out highest is fitting the test set, and the
#   number that follows is not a result.
#
#   Fidelity also answers the research question directly: run it with a
#   --probe from ANOTHER domain and it measures whether the vector still
#   carries the skill out of domain, with no benchmark in the loop at all.
#
# BASE MUST MATCH EXTRACTION. If the vector was built against a placebo, the
# fidelity measurement has to start from the same place, or the steered arm
# begins in a different state than the subtraction was measured from.
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_EVAL" eval
VEC="${1:?usage: ./04_measure_fidelity.sh <vectors.pt>}"
[ -f "$VEC" ] || VEC="$VECTORS/$(basename "$VEC")"
[ -f "$VEC" ] || fail "no such vector: $VEC"
SK="$(skill_path "${SKILL:-$SKILL_LIVEMATH}")"
ARGS=(--vectors "$VEC" --skill "$SK" --probe "${PROBE:-livemath}"
      --n "${NPROBE:-16}" --mode relative
      --bands "${BANDS:-32,40,48,24-40,36-52}"
      --gammas "${GAMMAS:-0.02,0.05,0.1,0.2,0.4}")
# a vs-placebo vector must be measured against that same placebo
case "$(basename "$VEC")" in
  *placebo*) ARGS+=(--baseline-skill "$(skill_path "${PLACEBO:-$SKILL_PLACEBO}")")
             note "measuring against placebo (matches how it was extracted)" ;;
  *)         note "measuring against no system message" ;;
esac
NO_SHARD=1 SHARDS=1 submit "fidelity_${MODEL_TAG}" "$PY_EVAL" "$KIT/src/fidelity.py" "${ARGS[@]}"
note "next: ./05_check_degeneration.sh on the setting this suggests"
