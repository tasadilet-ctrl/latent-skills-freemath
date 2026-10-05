#!/usr/bin/env bash
# SpreadsheetBench (AGENT) -- CONTROL. A vector whose SOURCE SKILL is the
# placebo itself.
#
#   ./run_control_placebo_only.sh <vectors.pt> <layers> <gamma>
#
# The null arm. This vector was built from text that contains NO procedure --
# only the shape, length and register of one. If steering with it moves the
# score as much as the real skill's vector does, then what the method
# transports is "instructional text was present", not the procedure.
#
# This is the cell that makes the other two interpretable. On LiveMath it is
# what settled the question.
#
# ===========================================================================
#  EXPENSIVE: ~25 h through the hooked server, against ~1 h for the same
#  vector in ../03_spreadsheetbench_single_turn/run_control_placebo_only.sh.
#  Prefer the single-turn arm unless you specifically need an agentic number.
# ===========================================================================
#
# Start the server FIRST:
#     ../00_setup/05_serve_model.sh steered <vectors.pt> <layers> <gamma>
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_AGENT" agent
require_data "$DATA/spreadsheetbench_verified_400"
VEC="${1:?usage: ./run_control_placebo_only.sh <vectors.pt> <layers> <gamma>}"
LAYERS="${2:?need layers}"; GAMMA="${3:?need gamma}"
[ -f "$VEC" ] || VEC="$VECTORS/$(basename "$VEC")"
[ -f "$VEC" ] || fail "no such vector: $VEC"
case "$(basename "$VEC")" in
  *placebo_*|*_placebo*) : ;;
  *) warn "'$(basename "$VEC")' does not look placebo-sourced -- the CONTROL"
     warn "needs a vector built FROM the placebo, not one merely extracted"
     warn "against it. See ../05_make_embedding_skills/03_extract_control_from_placebo.sh" ;;
esac
require_served_model
require_steering "$(basename "$VEC")"
submit "sb_agent_${MODEL_TAG}_control" "$PY_AGENT" "$KIT/src/run_sb_agent.py" \
  --condition baseline --limit "${LIMIT_SB:-400}" \
  --max-iterations "${MAX_ITER:-15}" --location-hint off
