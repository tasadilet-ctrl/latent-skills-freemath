#!/bin/bash
# WikiSkill on the MMLU-Pro T1 split (2026-11-24): the T1 table with WikiSkill skills in place of SkillOpt's.
# Per run R: evolve a skill set for 4b 8b 14b 27b (wiki_one.sh: K = 8 iterations, empty start, val 100 x 1),
# then test the run's 4 skills on every model (T 1.0, seed = R, 2048 tokens, 27B 4096) -> results_wiki/r<R>/.
# Baseline, one-line and elimination cells are copied from the T1 runs (results/r<R>/, same seed and settings),
# so the table's control columns are the T1 table's. Restartable.
#   run_wiki_t1.sh <first run> <last run>
set -uo pipefail
cd "$(dirname "$0")"
W=$HOME/skillopt_work; PY=$W/vllm_env/bin/python; DATA=$HOME/mcq_math/data/mmlupro_math_tq_sb.jsonl
declare -A HF=([4b]=Qwen/Qwen3-4B [8b]=Qwen/Qwen3-8B [14b]=Qwen/Qwen3-14B [27b]=Qwen/Qwen3.6-27B)
declare -A TOK=([4b]=2048 [8b]=2048 [14b]=2048 [27b]=4096)
mkdir -p skills_wiki results_wiki
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
gpus_free() {
  while :; do
    n=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 <= 2000' | wc -l)
    [ "$n" -ge 2 ] && return; sleep 300
  done
}
test_model() {  # <size> <R> <gpu>
  local s=$1 R=$2 g=$3
  CUDA_VISIBLE_DEVICES=$g VLLM_CACHE_ROOT=/dev/shm/$USER-wk-ev$g HF_HUB_OFFLINE=1 PATH=$W/vllm_env/bin:$PATH \
  MODEL_ID=${HF[$s]} $PY evaluate_mcq_t1.py --data $DATA \
    --skills skills_wiki/4b_r$R.md skills_wiki/8b_r$R.md skills_wiki/14b_r$R.md skills_wiki/27b_r$R.md \
    --temperature 1.0 --seed $R --attention-backend FLASHINFER --max-model-len 16384 \
    --max-new-tokens ${TOK[$s]} --out-dir results_wiki/r$R > logs_wiki_test_${s}_r$R.log 2>&1
  log "wiki test $s r$R rc=$?"
}
log "WIKI_T1 start $1-$2"
for R in $(seq $1 $2); do
  for s in 4b 8b 14b 27b; do
    out=$W/outputs/wiki_t1_${s}_r$R
    if [ ! -s $out/summary.json ]; then
      gpus_free; log "wiki train $s r$R start"
      bash wiki_one.sh $s $R >> train_driver.log 2>&1; log "wiki train $s r$R rc=$?"
    fi
    [ -s $out/summary.json ] || { log "WIKI_TRAIN_FAILED $s r$R"; exit 1; }
    cp $out/best_skill.md skills_wiki/${s}_r$R.md
  done
  mkdir -p results_wiki/r$R
  for f in results/r$R/*_baseline_s0of1.json results/r$R/*_oneliner_r${R}_s0of1.json results/r$R/*_elim_r${R}_s0of1.json; do
    [ -s $f ] && cp -n $f results_wiki/r$R/
  done
  gpus_free; log "wiki test r$R start"
  ( test_model 27b $R 0; test_model 4b $R 0 ) &
  ( test_model 14b $R 1; test_model 8b $R 1 ) &
  wait
  log "WIKI_RUN_DONE r$R"
done
log "WIKI_T1_DONE $1-$2"
