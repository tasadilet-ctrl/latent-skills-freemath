#!/bin/bash
# SuperGPQA math hard (500 q, mostly 10 options): no-skill and elimination-prompt accuracy for every model,
# before choosing models/split for SkillOpt. T 1.0, seed 1, same answer prompt/parser/tokens as the MMLU-Pro tests.
# Shortcut audit (2026-11-23): meta options 7 (never correct), longest option 11.2% (chance ~10), centroid 20.2%
# (101 questions, flag centroid_right) -> report centroid-wrong / centroid-right separately.
# GPU 0: 27B, 4B; GPU 1: 14B, 8B. Results: results_sg/base${MAXTOK:+_$MAXTOK}/.
set -uo pipefail
cd "$(dirname "$0")"
W=$HOME/skillopt_work; PY=$W/vllm_env/bin/python; DATA=$HOME/mcq_math/data/supergpqa_math_hard.jsonl
declare -A HF=([4b]=Qwen/Qwen3-4B [8b]=Qwen/Qwen3-8B [14b]=Qwen/Qwen3-14B [27b]=Qwen/Qwen3.6-27B)
declare -A TOK=([4b]=2048 [8b]=2048 [14b]=2048 [27b]=4096)
# MAXTOK overrides the per-model cap: at 2048 (27B 4096) 31-39% of SuperGPQA answers hit the cap and were forced
if [ -n "${MAXTOK:-}" ]; then for k in "${!TOK[@]}"; do TOK[$k]=$MAXTOK; done; fi
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
mkdir -p results_sg/base${MAXTOK:+_$MAXTOK} skills_sg
cp skills_t3/initial_elim.md skills_sg/elim.md
ev() {  # <size> <gpu>
  local s=$1 g=$2
  CUDA_VISIBLE_DEVICES=$g VLLM_CACHE_ROOT=/dev/shm/$USER-sg-$g HF_HUB_OFFLINE=1 PATH=$W/vllm_env/bin:$PATH \
  MODEL_ID=${HF[$s]} $PY evaluate_mcq_t1.py --data $DATA --skills none skills_sg/elim.md \
    --temperature 1.0 --seed 1 --attention-backend FLASHINFER --max-model-len 16384 \
    --max-new-tokens ${TOK[$s]} --out-dir results_sg/base${MAXTOK:+_$MAXTOK} > logs_sg_base_$s.log 2>&1
  log "sg base${MAXTOK:+ $MAXTOK} $s rc=$?"
}
log "sg base${MAXTOK:+ $MAXTOK} start"
( ev 27b 0; ev 4b 0 ) &
( ev 14b 1; ev 8b 1 ) &
wait
log "SG_BASE_DONE${MAXTOK:+_$MAXTOK}"
