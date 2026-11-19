#!/bin/bash
# T3 = T2 (Adil's split: train 100 / val 150 x 4 samples / test 255) with the Reasoning Gym sweep's best setting:
# batch 1, 1 epoch = 100 steps (rg_control/README.md: batch 1 test 82 vs 70-72 for batch 10/50/100, one run each).
# Starting skill: the hand-written elimination prompt (best T1 column, +1.9; Adil's protocol starts from a
# task-specific skill), written to skills_t3/initial_elim.md. Trains 4b 8b 14b 27b (cheapest first). Outputs: outputs/mq_t3_<size>_r<R>, skills_t3/, results_t3/.
#   run_t3.sh <first run> <last run>        e.g. run_t3.sh 1 1
set -uo pipefail
cd "$(dirname "$0")"; H=$(pwd)
W=$HOME/skillopt_work; PY=$W/vllm_env/bin/python; DATA=$HOME/mcq_math/data/mmlupro_math_tq_sb.jsonl
declare -A HF=([4b]=Qwen/Qwen3-4B [8b]=Qwen/Qwen3-8B [14b]=Qwen/Qwen3-14B [27b]=Qwen/Qwen3.6-27B)
declare -A TOK=([4b]=2048 [8b]=2048 [14b]=2048 [27b]=4096)
mkdir -p skills_t3 results_t3
printf '%s\n' "Reason step by step. Before answering, read all the options and eliminate those that contradict your result or the question's conditions; check units and signs. Then give the remaining option." > skills_t3/initial_elim.md
export SPLIT=mmlupro_math_t2 BATCH=1 MCQKIT_VAL_REPEATS=4
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
gpus_free() {  # both GPUs at <= 2 GB used
  while :; do
    n=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 <= 2000' | wc -l)
    [ "$n" -ge 2 ] && return; sleep 300
  done
}
test_model() {  # <size> <R> <gpu>
  local s=$1 R=$2 g=$3 tag; tag=$(basename ${HF[$s]} | tr A-Z a-z)
  ls results_t3/r$R/mmlupro_math_tq_sb_${tag}_27b_r${R}_s0of1.json >/dev/null 2>&1 && return 0
  CUDA_VISIBLE_DEVICES=$g VLLM_CACHE_ROOT=/dev/shm/$USER-t1-ev$g HF_HUB_OFFLINE=1 PATH=$W/vllm_env/bin:$PATH \
  MODEL_ID=${HF[$s]} $PY evaluate_mcq_t1.py --data $DATA \
    --skills none skills_t3/4b_r$R.md skills_t3/8b_r$R.md skills_t3/14b_r$R.md skills_t3/27b_r$R.md \
    --temperature 1.0 --seed $R --attention-backend FLASHINFER --max-model-len 16384 \
    --max-new-tokens ${TOK[$s]} --out-dir results_t3/r$R > logs_t3_test_${s}_r$R.log 2>&1
  log "t3 test $s r$R rc=$?"
}
for R in $(seq $1 $2); do
  for s in 4b 8b 14b 27b; do
    out=$W/outputs/mq_t3_${s}_r$R
    if [ ! -s $out/summary.json ]; then
      gpus_free; log "t3 train $s r$R start"
      RUN_NAME=mq_t3_${s}_r$R bash train_one.sh $s $R train.num_epochs=1 env.skill_init=$H/skills_t3/initial_elim.md >> train_driver.log 2>&1; log "t3 train $s r$R rc=$?"
    fi
    [ -s $out/best_skill.md ] || { log "T3_TRAIN_FAILED $s r$R"; exit 1; }
    grep -v "SLOW_UPDATE_\(START\|END\)" $out/best_skill.md > skills_t3/${s}_r$R.md
  done
  gpus_free; log "t3 test r$R start"
  ( test_model 27b $R 0; test_model 4b $R 0 ) &
  ( test_model 14b $R 1; test_model 8b $R 1 ) &
  wait
  log "T3_RUN_DONE r$R"
done
log "T3_ALL_DONE $1-$2"
