#!/usr/bin/env bash
# LiveMath -- BASELINE. The model gets the question and nothing else.
#
#   ./run_baseline.sh
#   MODEL_ID=Qwen/Qwen3-14B ./run_baseline.sh
#   LIMIT=50 ./run_baseline.sh            # quick check
#
# This is the reference every other LiveMath cell is compared against. It is
# not optional padding: without it a skill's effect cannot be separated from
# the model simply being good or bad at the benchmark.
#
# 608 questions, 5-way multiple choice, so chance is 20%. A cell scoring below
# 20% is broken, not bad -- see START_HERE.txt, "the truncation trap".
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_EVAL" eval
require_data "$DATA/livemath.jsonl"
submit "livemath_${MODEL_TAG}_baseline" "$PY_EVAL" "$KIT/src/evaluate.py" \
  --domain livemath --condition baseline \
  --limit "$LIMIT" --batch-size "$BS" --max-new-tokens "$MAXNEW"
