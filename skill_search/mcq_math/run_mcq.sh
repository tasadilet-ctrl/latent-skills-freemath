#!/usr/bin/env bash
# Qwen3-8B, thinking off, greedy vLLM: baseline / placebo / strength_audit / livemath_ts and its placebo
# on MMLU-Pro math (TheoremQA+SciBench) and SuperGPQA hard math. GPU1 only (GPU0 runs krsl2speech).
set -uo pipefail
cd "$(dirname "$0")"
export MODEL_ID=${MODEL_ID:-Qwen/Qwen3-8B} HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES=${GPU:-1} VLLM_CACHE_ROOT=/dev/shm/$USER-mcq
export PATH=$HOME/skillopt_work/vllm_env/bin:$PATH   # ninja for torch.compile (skillopt_local README)
PY=$HOME/skillopt_work/vllm_env/bin/python
for d in mmlupro_math_tq_sb supergpqa_math_hard; do
  $PY evaluate_vllm_mcq.py --data data/$d.jsonl --out-dir results \
    --skills none skills/placebo_matched.md skills/strength_audit.md skills/placebo_livemath_ts.md skills/livemath_ts.md
  echo "[mcq] DONE $d rc=$?"
done
$PY analyze_mcq.py results $(basename $MODEL_ID | tr A-Z a-z) | tee results/report.txt
echo "[mcq] ALL_DONE"
