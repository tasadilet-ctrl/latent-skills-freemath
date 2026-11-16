#!/bin/bash
# Queue step 1: per-question method hints (gen_hints.py, Qwen3.6-27B, thinking on, no options, no answer) for
# the 365 T1 test questions, then the T1 test protocol with the hint as each question's system prompt:
# 4 models x seeds 1-5, T 1.0. Results: results/r<R>/..._hint_r<R>_s0of1.json (same layout as the skill columns).
set -uo pipefail
cd "$(dirname "$0")"
W=$HOME/skillopt_work; PY=$W/vllm_env/bin/python; DATA=$HOME/mcq_math/data/mmlupro_math_tq_sb.jsonl
declare -A HF=([4b]=Qwen/Qwen3-4B [8b]=Qwen/Qwen3-8B [14b]=Qwen/Qwen3-14B [27b]=Qwen/Qwen3.6-27B)
declare -A TOK=([4b]=2048 [8b]=2048 [14b]=2048 [27b]=4096)
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
mkdir -p hints
python3 -c "import json;print(json.dumps([x['id'] for x in json.load(open('$W/mq_split/mmlupro_math_tq_sb/test/items.json'))]))" > hints/test_ids.json
if [ ! -s hints/hints_27b.json ]; then
  log "hints gen start"
  CUDA_VISIBLE_DEVICES=0 VLLM_CACHE_ROOT=/dev/shm/$USER-hint HF_HUB_OFFLINE=1 PATH=$W/vllm_env/bin:$PATH \
    MODEL_ID=Qwen/Qwen3.6-27B $PY gen_hints.py --data $DATA --ids hints/test_ids.json --out hints/hints_27b.json \
    > logs_hints_gen.log 2>&1
  log "hints gen rc=$? $(tail -1 logs_hints_gen.log)"
fi
[ -s hints/hints_27b.json ] || { log "HINTS_GEN_FAILED"; exit 1; }
for R in 1 2 3 4 5; do cp hints/hints_27b.json hints/hint_r$R.json; done
one() {  # <size> <R> <gpu>
  local s=$1 R=$2 g=$3 tag; tag=$(basename ${HF[$s]} | tr A-Z a-z)
  [ -s results/r$R/mmlupro_math_tq_sb_${tag}_hint_r${R}_s0of1.json ] && return 0
  CUDA_VISIBLE_DEVICES=$g VLLM_CACHE_ROOT=/dev/shm/$USER-t1-ev$g HF_HUB_OFFLINE=1 PATH=$W/vllm_env/bin:$PATH \
  MODEL_ID=${HF[$s]} $PY evaluate_mcq_t1.py --data $DATA --skills hints:hints/hint_r$R.json \
    --temperature 1.0 --seed $R --attention-backend FLASHINFER --max-model-len 16384 \
    --max-new-tokens ${TOK[$s]} --out-dir results/r$R > logs_test_hint_${s}_r$R.log 2>&1
  log "test hint $s r$R rc=$?"
}
( for R in 1 2 3 4 5; do one 27b $R 0; one 4b $R 0; done ) &
( for R in 1 2 3 4 5; do one 14b $R 1; one 8b $R 1; done ) &
wait
log "HINTS_DONE"
