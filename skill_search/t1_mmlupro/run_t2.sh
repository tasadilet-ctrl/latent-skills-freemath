#!/bin/bash
# T2 = run_t1.sh with Adil's bigger split (make_split_t2.py: train 100 / val 150 / test 255), batch 100 (each of the
# 4 steps sees all 100 train questions) and 4 samples per validation question (MCQKIT_VAL_REPEATS=4, patch_valrep.py).
# Outputs: outputs/mq_t2_<size>_r<R>, skills_t2/, results_t2/ (tests still run all 505; tables use the 255 test ids).
# The 5 runs of GUIDE_T1_5RUNS.md on MMLU-Pro math. Restartable: skips trainings with best_skill.md (and a
# finished summary.json) and tests whose output exists.
#
#   run_t1.sh <first run> <last run>        e.g. run_t1.sh 1 1, look at it, then run_t1.sh 2 5
#
# Per run R: 4 trainings (27b 14b 8b 4b; 2 GPUs, so one at a time), copy best_skill.md -> skills_t2/<size>_r<R>.md
# with SkillOpt's empty markers stripped, then baseline + the 4 skills on all 4 models (two models at a time).
# Waits for both GPUs to be free of other users' jobs (<= 2 GB) before each step.
set -uo pipefail
cd "$(dirname "$0")"; H=$(pwd)
W=$HOME/skillopt_work; PY=$W/vllm_env/bin/python; DATA=$HOME/mcq_math/data/mmlupro_math_tq_sb.jsonl
declare -A HF=([4b]=Qwen/Qwen3-4B [8b]=Qwen/Qwen3-8B [14b]=Qwen/Qwen3-14B [27b]=Qwen/Qwen3.6-27B)
declare -A TOK=([4b]=2048 [8b]=2048 [14b]=2048 [27b]=4096)
mkdir -p skills_t2 results_t2
export SPLIT=mmlupro_math_t2 BATCH=100 MCQKIT_VAL_REPEATS=4
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
gpus_free() {  # both GPUs at <= 2 GB used
  while :; do
    n=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 <= 2000' | wc -l)
    [ "$n" -ge 2 ] && return; sleep 300
  done
}
test_model() {  # <size> <R> <gpu>
  local s=$1 R=$2 g=$3 tag; tag=$(basename ${HF[$s]} | tr A-Z a-z)
  ls results_t2/r$R/mmlupro_math_tq_sb_${tag}_27b_r${R}_s0of1.json >/dev/null 2>&1 && return 0
  CUDA_VISIBLE_DEVICES=$g VLLM_CACHE_ROOT=/dev/shm/$USER-t1-ev$g HF_HUB_OFFLINE=1 PATH=$W/vllm_env/bin:$PATH \
  MODEL_ID=${HF[$s]} $PY evaluate_mcq_t1.py --data $DATA \
    --skills none skills_t2/4b_r$R.md skills_t2/8b_r$R.md skills_t2/14b_r$R.md skills_t2/27b_r$R.md \
    --temperature 1.0 --seed $R --attention-backend FLASHINFER --max-model-len 16384 \
    --max-new-tokens ${TOK[$s]} --out-dir results_t2/r$R > logs_t2_test_${s}_r$R.log 2>&1
  log "t2 test $s r$R rc=$?"
}
for R in $(seq $1 $2); do
  for s in 27b 14b 8b 4b; do
    out=$W/outputs/mq_t2_${s}_r$R
    if [ ! -s $out/summary.json ]; then
      gpus_free; log "t2 train $s r$R start"
      RUN_NAME=mq_t2_${s}_r$R bash train_one.sh $s $R >> train_driver.log 2>&1; log "t2 train $s r$R rc=$?"
    fi
    [ -s $out/best_skill.md ] || { log "T2_TRAIN_FAILED $s r$R"; exit 1; }
    grep -v "SLOW_UPDATE_\(START\|END\)" $out/best_skill.md > skills_t2/${s}_r$R.md
  done
  gpus_free; log "t2 test r$R start"
  ( test_model 27b $R 0; test_model 4b $R 0 ) &
  ( test_model 14b $R 1; test_model 8b $R 1 ) &
  wait
  log "T2_RUN_DONE r$R"
done
log "T2_ALL_DONE $1-$2"
