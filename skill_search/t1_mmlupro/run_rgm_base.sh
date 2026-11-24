#!/bin/bash
# Reasoning Gym decimal_arithmetic as 10-option MCQ (make_rg_mcq.py, 2026-11-24): no-skill and elimination-prompt
# accuracy for every model before SkillOpt, same prompt/parser/forcing as the MMLU-Pro and SuperGPQA tests,
# T 1.0, seed 1, 4096 new tokens. Each lane waits until its GPU has <= 2 GB used by others.
# Lane GPU 0: 4B, 14B; lane GPU 1: 8B, 27B. Results: results_rgm/base/ (score the 250 test ids).
set -uo pipefail
cd "$(dirname "$0")"
W=$HOME/skillopt_work; PY=$W/vllm_env/bin/python; DATA=$HOME/mcq_math/data/rg_decimal_mcq.jsonl
declare -A HF=([4b]=Qwen/Qwen3-4B [8b]=Qwen/Qwen3-8B [14b]=Qwen/Qwen3-14B [27b]=Qwen/Qwen3.6-27B)
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
gpu_free() { until [ "$(nvidia-smi -i $1 --query-gpu=memory.used --format=csv,noheader,nounits)" -le 2000 ]; do sleep 300; done; }
mkdir -p results_rgm/base skills_rgm
cp skills_t3/initial_elim.md skills_rgm/elim.md
ev() {  # <size> <gpu>
  local s=$1 g=$2
  gpu_free $g
  CUDA_VISIBLE_DEVICES=$g VLLM_CACHE_ROOT=/dev/shm/$USER-rgm-$g HF_HUB_OFFLINE=1 PATH=$W/vllm_env/bin:$PATH \
  MODEL_ID=${HF[$s]} $PY evaluate_mcq_t1.py --data $DATA --skills none skills_rgm/elim.md \
    --temperature 1.0 --seed 1 --attention-backend FLASHINFER --max-model-len 16384 \
    --max-new-tokens 4096 --out-dir results_rgm/base > logs_rgm_base_$s.log 2>&1
  log "rgm base $s rc=$?"
}
log "rgm base start"
( ev 4b 0; ev 14b 0 ) &
( ev 8b 1; ev 27b 1 ) &
wait
log "RGM_BASE_DONE"
