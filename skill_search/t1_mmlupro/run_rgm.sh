#!/bin/bash
# SkillOpt on Reasoning Gym decimal_arithmetic as 10-option MCQ (make_rg_mcq.py, 2026-11-24), T2 settings: split
# rg_decimal_mcq (train 100 / val 150 x 4 samples / test 250), batch 100 (BATCH env overrides), 4 epochs, starting
# skill = the elimination prompt, both models T 1.0, 4096 answer tokens. Each trained model is then tested with no
# skill, the elimination prompt and its own skill (T 1.0, seed = run) on GPU 0 -> results_rgm/b<BATCH>/r<R>/.
#   [BATCH=1] run_rgm.sh <first run> <last run> <size...>      e.g. run_rgm.sh 1 1 4b 8b 14b
set -uo pipefail
cd "$(dirname "$0")"; H=$(pwd)
W=$HOME/skillopt_work; PY=$W/vllm_env/bin/python; DATA=$HOME/mcq_math/data/rg_decimal_mcq.jsonl
declare -A HF=([4b]=Qwen/Qwen3-4B [8b]=Qwen/Qwen3-8B [14b]=Qwen/Qwen3-14B [27b]=Qwen/Qwen3.6-27B)
TOK=4096
R1=$1; R2=$2; shift 2; SIZES="$*"
export SPLIT=rg_decimal_mcq BATCH=${BATCH:-100} MCQKIT_VAL_REPEATS=4
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
gpus_free() {
  while :; do
    n=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 <= 2000' | wc -l)
    [ "$n" -ge 2 ] && return; sleep 300
  done
}
mkdir -p skills_rgm
cp skills_t3/initial_elim.md skills_rgm/elim.md
for R in $(seq $R1 $R2); do
  for s in $SIZES; do
    name=rgm_${s}_b${BATCH}_r$R; out=$W/outputs/$name
    if [ ! -s $out/summary.json ]; then
      gpus_free; log "rgm train $s b$BATCH r$R start"
      RUN_NAME=$name bash train_one.sh $s $R env.skill_init=$H/skills_rgm/elim.md env.max_completion_tokens=$TOK >> train_driver.log 2>&1
      log "rgm train $s b$BATCH r$R rc=$?"
    fi
    [ -s $out/best_skill.md ] || { log "RGM_TRAIN_FAILED $s b$BATCH r$R"; continue; }
    grep -v "SLOW_UPDATE_\(START\|END\)" $out/best_skill.md > skills_rgm/${s}_b${BATCH}_r$R.md
    gpus_free
    CUDA_VISIBLE_DEVICES=0 VLLM_CACHE_ROOT=/dev/shm/$USER-rgm-0 HF_HUB_OFFLINE=1 PATH=$W/vllm_env/bin:$PATH \
    MODEL_ID=${HF[$s]} $PY evaluate_mcq_t1.py --data $DATA --skills none skills_rgm/elim.md skills_rgm/${s}_b${BATCH}_r$R.md \
      --temperature 1.0 --seed $R --attention-backend FLASHINFER --max-model-len 16384 \
      --max-new-tokens $TOK --out-dir results_rgm/b$BATCH/r$R > logs_rgm_test_${s}_b${BATCH}_r$R.log 2>&1
    log "rgm test $s b$BATCH r$R rc=$?"
  done
done
log "RGM_DONE b$BATCH $R1-$R2 $SIZES"
