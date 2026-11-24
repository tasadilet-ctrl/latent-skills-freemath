#!/bin/bash
# The T1-style 5-run table on Reasoning Gym decimal_arithmetic as 10-option MCQ (make_rg_mcq.py, 2026-11-24).
# Restartable: skips trainings with a summary.json and tests whose output exists.
#   run_rgm_t1.sh <first run> <last run>
# Per run R: SkillOpt for 27b 14b 8b 4b (one at a time, both GPUs; split rg_decimal_mcq = train 100 / val 150 x 4
# samples / test 250, batch 100, 4 epochs, starting skill = the elimination prompt, T 1.0, 4096 answer tokens;
# the run-1 4b/8b/14b trainings come from run_rgm.sh, same names and settings), then on every model: no skill,
# one-line prompt, elimination prompt and the run's 4 skills (T 1.0, seed = run) -> results_rgm_t1/r<R>/.
# Waits for run_rgm.sh's run 1 to finish and for both GPUs to be free of other users' jobs (<= 2 GB).
set -uo pipefail
cd "$(dirname "$0")"; H=$(pwd)
W=$HOME/skillopt_work; PY=$W/vllm_env/bin/python; DATA=$HOME/mcq_math/data/rg_decimal_mcq.jsonl
declare -A HF=([4b]=Qwen/Qwen3-4B [8b]=Qwen/Qwen3-8B [14b]=Qwen/Qwen3-14B [27b]=Qwen/Qwen3.6-27B)
TOK=4096; SK=skills_rgm_t1; RES=results_rgm_t1
export SPLIT=rg_decimal_mcq BATCH=100 MCQKIT_VAL_REPEATS=4
mkdir -p $SK $RES skills_rgm
cp skills_t3/initial_elim.md skills_rgm/elim.md
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
gpus_free() {
  while :; do
    n=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 <= 2000' | wc -l)
    [ "$n" -ge 2 ] && return; sleep 300
  done
}
test_model() {  # <size> <R> <gpu>
  local s=$1 R=$2 g=$3
  CUDA_VISIBLE_DEVICES=$g VLLM_CACHE_ROOT=/dev/shm/$USER-rgm-ev$g HF_HUB_OFFLINE=1 PATH=$W/vllm_env/bin:$PATH \
  MODEL_ID=${HF[$s]} $PY evaluate_mcq_t1.py --data $DATA \
    --skills none $SK/oneliner_r$R.md $SK/elim_r$R.md $SK/4b_r$R.md $SK/8b_r$R.md $SK/14b_r$R.md $SK/27b_r$R.md \
    --temperature 1.0 --seed $R --attention-backend FLASHINFER --max-model-len 16384 \
    --max-new-tokens $TOK --out-dir $RES/r$R > logs_rgm_t1_test_${s}_r$R.log 2>&1
  log "rgm t1 test $s r$R rc=$?"
}
until grep -q "RGM_DONE b100 1-1" jobs.txt; do sleep 120; done
log "RGM_T1 start $1-$2"
for R in $(seq $1 $2); do
  printf '%s\n' "Solve the task step by step and check your work before answering." > $SK/oneliner_r$R.md
  cp skills_rgm/elim.md $SK/elim_r$R.md
  for s in 27b 14b 8b 4b; do
    name=rgm_${s}_b100_r$R; out=$W/outputs/$name
    if [ ! -s $out/summary.json ]; then
      gpus_free; log "rgm train $s b100 r$R start"
      RUN_NAME=$name bash train_one.sh $s $R env.skill_init=$H/skills_rgm/elim.md env.max_completion_tokens=$TOK >> train_driver.log 2>&1
      log "rgm train $s b100 r$R rc=$?"
    fi
    [ -s $out/best_skill.md ] || { log "RGM_TRAIN_FAILED $s r$R"; exit 1; }
    grep -v "SLOW_UPDATE_\(START\|END\)" $out/best_skill.md > $SK/${s}_r$R.md
  done
  gpus_free; log "rgm t1 test r$R start"
  ( test_model 27b $R 0; test_model 4b $R 0 ) &
  ( test_model 14b $R 1; test_model 8b $R 1 ) &
  wait
  log "RGM_RUN_DONE r$R"
done
log "RGM_T1_DONE $1-$2"
