#!/bin/bash
# SkillOpt on SuperGPQA math hard (2026-11-23), T2 settings: split supergpqa_math_t2 (make_split_sg.py: train 100 /
# val 150 x 4 samples / test 250), batch 100, 4 epochs, starting skill = the elimination prompt, both models T 1.0.
# Each trained model is then tested with no skill, the elimination prompt and its own skill (T 1.0, seed = run) on
# GPU 0 -> results_sg/r<R>/ (score the 250 test ids; centroid-right / centroid-wrong separately).
#   [MAXTOK=8192] run_sg.sh <first run> <last run> <size...>      e.g. MAXTOK=8192 run_sg.sh 1 1 4b 8b 14b
# MAXTOK sets the answer cap in training (env.max_completion_tokens, after train_one's own) and test.
set -uo pipefail
cd "$(dirname "$0")"; H=$(pwd)
W=$HOME/skillopt_work; PY=$W/vllm_env/bin/python; DATA=$HOME/mcq_math/data/supergpqa_math_hard.jsonl
declare -A HF=([4b]=Qwen/Qwen3-4B [8b]=Qwen/Qwen3-8B [14b]=Qwen/Qwen3-14B [27b]=Qwen/Qwen3.6-27B)
declare -A TOK=([4b]=2048 [8b]=2048 [14b]=2048 [27b]=4096)
# MAXTOK overrides the per-model cap: at 2048 (27B 4096) 31-39% of SuperGPQA answers hit the cap and were forced
if [ -n "${MAXTOK:-}" ]; then for k in "${!TOK[@]}"; do TOK[$k]=$MAXTOK; done; fi
R1=$1; R2=$2; shift 2; SIZES="$*"
export SPLIT=supergpqa_math_t2 BATCH=100 MCQKIT_VAL_REPEATS=4
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
gpus_free() {
  while :; do
    n=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 <= 2000' | wc -l)
    [ "$n" -ge 2 ] && return; sleep 300
  done
}
mkdir -p skills_sg
cp skills_t3/initial_elim.md skills_sg/elim.md
until grep -q "SG_BASE_DONE${MAXTOK:+_$MAXTOK}" jobs.txt; do sleep 120; done
for R in $(seq $R1 $R2); do
  for s in $SIZES; do
    out=$W/outputs/sg_t2_${s}${MAXTOK:+_$MAXTOK}_r$R
    if [ ! -s $out/summary.json ]; then
      gpus_free; log "sg train $s r$R start"
      RUN_NAME=sg_t2_${s}${MAXTOK:+_$MAXTOK}_r$R bash train_one.sh $s $R env.skill_init=$H/skills_sg/elim.md env.max_completion_tokens=${TOK[$s]} >> train_driver.log 2>&1
      log "sg train $s r$R rc=$?"
    fi
    [ -s $out/best_skill.md ] || { log "SG_TRAIN_FAILED $s r$R"; continue; }
    grep -v "SLOW_UPDATE_\(START\|END\)" $out/best_skill.md > skills_sg/${s}${MAXTOK:+_$MAXTOK}_r$R.md
    gpus_free
    CUDA_VISIBLE_DEVICES=0 VLLM_CACHE_ROOT=/dev/shm/$USER-sg-0 HF_HUB_OFFLINE=1 PATH=$W/vllm_env/bin:$PATH \
    MODEL_ID=${HF[$s]} $PY evaluate_mcq_t1.py --data $DATA --skills none skills_sg/elim.md skills_sg/${s}${MAXTOK:+_$MAXTOK}_r$R.md \
      --temperature 1.0 --seed $R --attention-backend FLASHINFER --max-model-len 16384 \
      --max-new-tokens ${TOK[$s]} --out-dir results_sg${MAXTOK:+_$MAXTOK}/r$R > logs_sg_test_${s}_r$R.log 2>&1
    log "sg test $s r$R rc=$?"
  done
done
log "SG_DONE $R1-$R2 $SIZES"
