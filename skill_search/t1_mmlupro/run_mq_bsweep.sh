#!/bin/bash
# Batch-size sweep for SkillOpt on MMLU-Pro math (2026-11-25), the Reasoning Gym sweep's design (run_bsweep.sh) on
# MMLU-Pro: Qwen3-14B answers, Qwen3.6-27B edits (both T 1.0), T2 split (train 100 / val 150 x 4 samples / test 255),
# SkillOpt's default starting skill, seed 1. Batch 100 50 20 10 1; 4 epochs each (400 training examples seen, 4 to
# 40 steps) except batch 1: 1 epoch (100 steps), as in the RG sweep. Batch 100 = T2 run 1 (mq_t2_14b_r1, same
# settings), reused. Shortest first so the table fills early. After each training: Qwen3-14B with no skill and every
# finished skill, T 1.0, seeds 1 2 3 -> results_bs/s<seed>/ (score the 255 T2 test ids).
set -uo pipefail
cd "$(dirname "$0")"
W=$HOME/skillopt_work; PY=$W/vllm_env/bin/python; DATA=$HOME/mcq_math/data/mmlupro_math_tq_sb.jsonl
export SPLIT=mmlupro_math_t2 MCQKIT_VAL_REPEATS=4
mkdir -p skills_bs results_bs
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
gpus_free() {
  while :; do
    n=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 <= 2000' | wc -l)
    [ "$n" -ge 2 ] && return; sleep 300
  done
}
strip() { grep -v "SLOW_UPDATE_\(START\|END\)" $1 > $2; }
test_all() {  # no skill + every finished skill on Qwen3-14B, seeds 1-3, GPU 0 and 1 in parallel
  gpus_free
  for s in 1 2 3; do
    g=$(( (s - 1) % 2 ))
    ( CUDA_VISIBLE_DEVICES=$g VLLM_CACHE_ROOT=/dev/shm/$USER-bs-$g HF_HUB_OFFLINE=1 PATH=$W/vllm_env/bin:$PATH \
      MODEL_ID=Qwen/Qwen3-14B $PY evaluate_mcq_t1.py --data $DATA --skills none $(ls skills_bs/b*.md) \
        --temperature 1.0 --seed $s --attention-backend FLASHINFER --max-model-len 16384 \
        --max-new-tokens 2048 --out-dir results_bs/s$s > logs_bs_test_s$s.log 2>&1; log "bs test s$s rc=$?" ) &
    [ $g = 1 ] && wait
  done
  wait
}
log "MQ_BSWEEP start"
strip $W/outputs/mq_t2_14b_r1/best_skill.md skills_bs/b100.md
for B in 50 20 10 1; do
  E=4; [ $B = 1 ] && E=1
  out=$W/outputs/mq_bs_14b_b$B
  if [ ! -s $out/summary.json ]; then
    gpus_free; log "bs train b$B e$E start"
    BATCH=$B RUN_NAME=mq_bs_14b_b$B bash train_one.sh 14b 1 train.num_epochs=$E >> train_driver.log 2>&1
    log "bs train b$B rc=$?"
  fi
  [ -s $out/best_skill.md ] && strip $out/best_skill.md skills_bs/b$B.md || log "BS_TRAIN_FAILED b$B"
  test_all
done
log "MQ_BSWEEP_DONE"
