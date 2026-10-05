#!/usr/bin/env bash
# SpreadsheetBench (AGENT) -- EMBEDDING SKILL, extracted against a PLACEBO system prompt
# B1 -- the CONTROLLED arm
#
#   ./run_embed_from_placebo.sh <vectors.pt> <layers> <gamma>
#
# The vector is
#     mean activations under [placebo + skill]  -  mean under [placebo]
# so the length-matched placebo sits on BOTH sides and cancels. What survives
# is meant to be the procedure, not "a system prompt exists".
#
# This is the arm the study's conclusion rests on. Compare it with
# run_embed_from_nothing.sh.
#
# ===========================================================================
#  THIS CELL IS EXPENSIVE. READ BEFORE LAUNCHING.
# ===========================================================================
#  Steering needs the residual stream, which vLLM does not expose, so this
#  must run through the HOOKED server (src/serve_hooked.py) -- plain HF
#  transformers, serial, no batching. Measured here: ~25 h for a 400-task
#  agent cell, against ~1 h for the same vector through
#  ../03_spreadsheetbench_single_turn/run_embed_from_placebo.sh.
#
#  If you want a SpreadsheetBench embedding number and not specifically an
#  AGENTIC one, run the single-turn arm instead. It is a different row in the
#  matrix, not a worse version of this one.
# ===========================================================================
#
# Start the server FIRST, in its own terminal or job:
#     ../00_setup/05_serve_model.sh steered <vectors.pt> <layers> <gamma>
#
# Note there is no --condition embed. The adapter asks the SERVER whether it
# is steering and labels the cell from the answer, so the command below is the
# baseline command pointed at a steered server. require_steering refuses to
# run if the server is not actually steering -- otherwise this would silently
# write a second baseline.
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_AGENT" agent
require_data "$DATA/spreadsheetbench_verified_400"
VEC="${1:?usage: ./run_embed_from_placebo.sh <vectors.pt> <layers> <gamma>}"
LAYERS="${2:?need layers, e.g. 34}"; GAMMA="${3:?need gamma, e.g. 0.3}"
[ -f "$VEC" ] || VEC="$VECTORS/$(basename "$VEC")"
[ -f "$VEC" ] || fail "no such vector: $VEC  (build one in ../05_make_embedding_skills/)"
require_served_model
require_steering "$(basename "$VEC")"
submit "sb_agent_${MODEL_TAG}_embed_from_placebo" "$PY_AGENT" "$KIT/src/run_sb_agent.py" \
  --condition baseline --limit "${LIMIT_SB:-400}" \
  --max-iterations "${MAX_ITER:-15}" --location-hint off
