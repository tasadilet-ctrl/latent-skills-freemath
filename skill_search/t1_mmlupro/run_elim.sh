#!/bin/bash
# Test-only column: a hand-written option-elimination prompt (external review suggestion, 2026-11-18) as the
# system prompt, scored in runs 1-5 on all 4 models with the same runner, seed (= run),
# temperature and token limits as run_t1.sh. No training; the baseline is not re-run. Restartable.
#   run_elim.sh                (from ~/t1_mq)
set -uo pipefail
cd "$(dirname "$0")"
W=$HOME/skillopt_work; PY=$W/vllm_env/bin/python; DATA=$HOME/mcq_math/data/mmlupro_math_tq_sb.jsonl
declare -A HF=([4b]=Qwen/Qwen3-4B [8b]=Qwen/Qwen3-8B [14b]=Qwen/Qwen3-14B [27b]=Qwen/Qwen3.6-27B)
declare -A TOK=([4b]=2048 [8b]=2048 [14b]=2048 [27b]=4096)
for R in 1 2 3 4 5; do
  printf '%s\n' "Reason step by step. Before answering, read all the options and eliminate those that contradict your result or the question's conditions; check units and signs. Then give the remaining option." > skills/elim_r$R.md
done
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
gpus_free() {
  while :; do
    n=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 <= 2000' | wc -l)
    [ "$n" -ge 2 ] && return; sleep 300
  done
}
one() {  # <size> <R> <gpu>
  local s=$1 R=$2 g=$3 tag; tag=$(basename ${HF[$s]} | tr A-Z a-z)
  [ -s results/r$R/mmlupro_math_tq_sb_${tag}_elim_r${R}_s0of1.json ] && return 0
  CUDA_VISIBLE_DEVICES=$g VLLM_CACHE_ROOT=/dev/shm/$USER-t1-ev$g HF_HUB_OFFLINE=1 PATH=$W/vllm_env/bin:$PATH \
  MODEL_ID=${HF[$s]} $PY evaluate_mcq_t1.py --data $DATA --skills skills/elim_r$R.md \
    --temperature 1.0 --seed $R --attention-backend FLASHINFER --max-model-len 16384 \
    --max-new-tokens ${TOK[$s]} --out-dir results/r$R > logs_test_elim_${s}_r$R.log 2>&1
  log "test elim $s r$R rc=$?"
}
gpus_free; log "ELIM start"
( for R in 1 2 3 4 5; do one 27b $R 0; one 4b $R 0; done ) &
( for R in 1 2 3 4 5; do one 14b $R 1; one 8b $R 1; done ) &
wait
log "ELIM_DONE"
