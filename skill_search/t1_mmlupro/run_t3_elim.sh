#!/bin/bash
# T3 control column: the elimination prompt alone (T3's starting skill, no training) on the T2/T3 test, every model,
# T 1.0, seed = run, same settings as run_t3.sh's test. Waits for QUEUE6_DONE (run_queue6.sh), then GPU 0: 27B, 4B;
# GPU 1: 14B, 8B. Condition name elim_r<R> -> results_t3/r<R>/, the "elim" column of make_table.sh t3.
#   run_t3_elim.sh <first run> <last run>
set -uo pipefail
cd "$(dirname "$0")"
W=$HOME/skillopt_work; PY=$W/vllm_env/bin/python; DATA=$HOME/mcq_math/data/mmlupro_math_tq_sb.jsonl
declare -A HF=([4b]=Qwen/Qwen3-4B [8b]=Qwen/Qwen3-8B [14b]=Qwen/Qwen3-14B [27b]=Qwen/Qwen3.6-27B)
declare -A TOK=([4b]=2048 [8b]=2048 [14b]=2048 [27b]=4096)
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
gpus_free() {
  while :; do
    n=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 <= 2000' | wc -l)
    [ "$n" -ge 2 ] && return; sleep 300
  done
}
ev() {  # <size> <R> <gpu>
  local s=$1 R=$2 g=$3 tag; tag=$(basename ${HF[$s]} | tr A-Z a-z)
  ls results_t3/r$R/mmlupro_math_tq_sb_${tag}_elim_r${R}_s0of1.json >/dev/null 2>&1 && return 0
  CUDA_VISIBLE_DEVICES=$g VLLM_CACHE_ROOT=/dev/shm/$USER-t3e-$g HF_HUB_OFFLINE=1 PATH=$W/vllm_env/bin:$PATH \
  MODEL_ID=${HF[$s]} $PY evaluate_mcq_t1.py --data $DATA --skills skills_t3/elim_r$R.md \
    --temperature 1.0 --seed $R --attention-backend FLASHINFER --max-model-len 16384 \
    --max-new-tokens ${TOK[$s]} --out-dir results_t3/r$R > logs_t3e_${s}_r$R.log 2>&1
  log "t3 elim $s r$R rc=$?"
}
until grep -q QUEUE6_DONE jobs.txt; do sleep 600; done
for R in $(seq $1 $2); do
  cp skills_t3/initial_elim.md skills_t3/elim_r$R.md
  gpus_free; log "t3 elim r$R start"
  ( ev 27b $R 0; ev 4b $R 0 ) &
  ( ev 14b $R 1; ev 8b $R 1 ) &
  wait
done
log "T3_ELIM_DONE $1-$2"
