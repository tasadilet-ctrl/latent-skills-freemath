#!/usr/bin/env bash
# LiveMath 556 (minus SkillOpt train+val), Qwen3-8B, thinking off, greedy vLLM, at 2048 and 4096 new tokens.
set -uo pipefail
cd "$(dirname "$0")"
export MODEL_ID=Qwen/Qwen3-8B HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES=${GPU:-1} VLLM_CACHE_ROOT=/dev/shm/$USER-mcq
export PATH=$HOME/skillopt_work/vllm_env/bin:$PATH
PY=$HOME/skillopt_work/vllm_env/bin/python
for T in 2048 4096; do
  $PY evaluate_vllm_mcq.py --data data/livemath556.jsonl --out-dir results_lm_$T --max-new-tokens $T --max-model-len 8192 \
    --skills none skills/placebo_matched.md skills/strength_audit.md skills/placebo_livemath_ts.md skills/livemath_ts.md
  echo "[lm] DONE $T rc=$?"
done
$PY analyze_livemath_budget.py results_lm_2048 results_lm_4096 | tee results_lm_report.txt
echo "[lm] ALL_DONE"
