#!/usr/bin/env bash
# LiveMath -- TEXT SKILL. The skill is pasted in as the system prompt.
#
#   ./run_text_skill.sh
#   SKILL_LIVEMATH=decompose_verify.md ./run_text_skill.sh     # a different skill
#
# The skill is NOT a file the model chooses to open. Its whole text is the
# system message, so the model always has it and cannot fail to load it. That
# matters: a progressive-disclosure skill would make a null result mean "the
# agent never read it" rather than "the procedure did not help". A steering
# vector is applied unconditionally, so its text counterpart must be too.
#
# THE SKILL IS strength_audit.md -- one canonical file, no versions. It
# replaced compare_claims.md (v3) on 2026-10-05; all compare_claims drafts are
# in skills/archive/ under *_SUPERSEDED names, so a run pointed at the old name
# fails loudly instead of silently running the wrong text. The history is in
# skills/notes/README.md, including why compare_claims v1 HURT (~24% against a
# 26.15% baseline -- it ranked candidates by strength before checking
# derivability).
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_EVAL" eval
require_data "$DATA/livemath.jsonl"
SK="$(skill_path "$SKILL_LIVEMATH")"
[ -f "$SK" ] || fail "no such skill: $SK"
note "skill: $(basename "$SK")"
submit "livemath_${MODEL_TAG}_text" "$PY_EVAL" "$KIT/src/evaluate.py" \
  --domain livemath --condition text --skill "$SK" \
  --limit "$LIMIT" --batch-size "$BS" --max-new-tokens "$MAXNEW"
