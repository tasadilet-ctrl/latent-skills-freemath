#!/usr/bin/env bash
# OfficeQA (AGENT) -- EMBEDDING SKILL, extracted against NO system message (B2, UNCONTROLLED)
#
#   ./run_embed_from_nothing.sh <vectors.pt> <layers> <gamma>
#
# vector = mean activations under [skill] - mean under [no system message].
# UNCONTROLLED BY CONSTRUCTION: the contrast holds the procedure AND the bare
# presence of instructional text, with nothing separating them. It exists to be
# compared against the controlled arm; never report it alone.
#
# NEEDS THE HOOKED SERVER, not vLLM: steering reads the residual stream and
# vLLM does not expose it. Start it first, in its own terminal or job:
#     ../00_setup/05_serve_model.sh steered <vectors.pt> <layers> <gamma>
#
# That server is serial and unbatched, so this is slow -- budget many hours
# for 239 questions, and start with LIMIT_OQA=20 to confirm the plumbing.
#
# There is no --condition embed: the adapter asks the SERVER whether it is
# steering and labels the cell from the answer. require_steering refuses to
# run against a plain server, which would otherwise quietly write a second
# baseline.
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_AGENT" agent
require_data "$DATA/officeqa_docs"
VEC="${1:?usage: ./run_embed_from_nothing.sh <vectors.pt> <layers> <gamma>}"
LAYERS="${2:?need layers}"; GAMMA="${3:?need gamma}"
[ -f "$VEC" ] || VEC="$VECTORS/$(basename "$VEC")"
[ -f "$VEC" ] || fail "no such vector: $VEC  (build one in ../05_make_embedding_skills/)"
require_served_model
require_steering "$(basename "$VEC")"
submit "oqa_${MODEL_TAG}_embed_from_nothing" "$PY_AGENT" "$KIT/src/run_oqa_agent.py" \
  --condition baseline --limit "${LIMIT_OQA:-239}" \
  --max-iterations "${MAX_ITER:-25}"
