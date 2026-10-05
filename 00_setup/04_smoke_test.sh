#!/usr/bin/env bash
# Prove the plumbing works before spending GPU-hours on the matrix.
#
#   ./00_setup/04_smoke_test.sh
#
# Checks, in order:
#   1. the model loads and its decoder ModuleList resolves
#   2. the chat template renders with enable_thinking=False
#   3. capture hooks return one hidden state per layer
#   4. a with-skill / without-skill contrast gives a non-degenerate direction
#   5. injection changes the generated text, and gamma=0 is a no-op
#   6. a 20-question LiveMath cell runs end to end and writes a result file
#
# Step 6 is the one that matters most: it is the whole path, in miniature. If
# it passes, a full run will not fail for a reason you could have caught in
# two minutes. Takes ~5 min on an 8B.
set -uo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$KIT/lib/common.sh"
require_env "$PY_EVAL" eval
require_data "$DATA/livemath.jsonl"

say "1-5  hooks, template, capture, contrast, injection"
"$PY_EVAL" "$KIT/src/smoke_test.py" || fail "smoke_test.py failed -- stop here and read the output above"

say "6  a 20-question LiveMath cell, end to end"
LIMIT=20 SHARDS=1 GPU="${GPU%%,*}" RUNNER=local \
  submit smoke_livemath "$PY_EVAL" "$KIT/src/evaluate.py" \
    --domain livemath --condition baseline --limit 20 --batch-size 4 \
    --max-new-tokens 512

latest=$(ls -t "$RESULTS"/livemath_*baseline*.json 2>/dev/null | head -1)
[ -n "$latest" ] || fail "no result file was written"
say "Smoke test PASSED"
note "wrote $latest"
note ""
note "Now read START_HERE.txt section 'the three traps' before launching the matrix."
