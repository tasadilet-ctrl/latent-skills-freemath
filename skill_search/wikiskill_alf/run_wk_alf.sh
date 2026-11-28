#!/bin/bash
# WikiSkill on ALFWorld (2026-11-28): Adil's setup (wiki_skill branch: jobs/evolve.sbatch + runner.py) with the
# `alf` domain from runner_alf.py, on our 2-GPU box instead of SLURM.
#   GPU0 = TARGET  (plays the games; thinking off, as Adil's jobs; vLLM flags as evolve.sbatch)
#   GPU1 = OPT     Qwen/Qwen3.8-27B (wiki maintainer + skill proposer; thinking on, tool calls)
# Per run R and target: new workspace (train 39 / val 18 / test 134), 8 iterations (the paper's 0-7), export
# final_skills.md, then test it on the 134 test games with the same inference agent. Run 1 also tests no skill.
#   run_wk_alf.sh <first run> <last run> [targets...]     targets default: 4b 9b 27b
#   SMOKE=2 ITERS=1 run_wk_alf.sh 0 0 4b                  quick check (2 games per split, 1 iteration)
set -uo pipefail
H=$(cd "$(dirname "$0")" && pwd)
WK=$HOME/wikiskill_adil/wikiskill
SO=$HOME/skillopt_work/SkillOpt
PY=$SO/.venv/bin/python              # has openai, requests and SkillOpt's ALFWorld deps
VENV=$HOME/skillopt_work/vllm_env
OUT=$HOME/wk_alf; mkdir -p $OUT/logs
declare -A HF=([4b]=Qwen/Qwen3.5-4B [9b]=Qwen/Qwen3.5-9B [27b]=Qwen/Qwen3.8-27B)
OPT=Qwen/Qwen3.8-27B
R1=$1; R2=$2; shift 2; SIZES="${*:-4b 9b 27b}"
export HF_HUB_OFFLINE=1 PATH=$VENV/bin:$PATH ALFWORLD_DATA=$HOME/.cache/alfworld PYTHONUNBUFFERED=1
export WK_DIR=$WK SKILLOPT_DIR=$SO WIKISKILL_WORKERS=${WORKERS:-40}
log() { echo "$(date '+%F %T') $*" | tee -a $HOME/t1_mq/jobs.txt; }
gpus_free() {
  while :; do
    n=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 <= 2000' | wc -l)
    [ "$n" -ge 2 ] && return; sleep 300
  done
}
free_port() { while :; do p=$((20000 + RANDOM % 20000)); ss -ltn | awk '{print $4}' | grep -q ":$p\$" || { echo $p; return; }; done; }
start_servers() {  # <target hf id> <tag>
  PT=$(free_port); PO=$(free_port); while [ "$PO" = "$PT" ]; do PO=$(free_port); done
  CUDA_VISIBLE_DEVICES=0 VLLM_CACHE_ROOT=/dev/shm/$USER-wkt vllm serve $1 --port $PT \
    --max-model-len 65536 --gpu-memory-utilization 0.9 --enable-prefix-caching --attention-backend FLASHINFER \
    --max-num-seqs 128 --reasoning-parser qwen3 --enable-auto-tool-choice --tool-call-parser qwen3_xml \
    > $OUT/logs/vllm_target_$2.log 2>&1 &
  ST=$!
  CUDA_VISIBLE_DEVICES=1 VLLM_CACHE_ROOT=/dev/shm/$USER-wko vllm serve $OPT --port $PO \
    --max-model-len 131072 --gpu-memory-utilization 0.92 --enable-prefix-caching --attention-backend FLASHINFER \
    --max-num-seqs 32 --reasoning-parser qwen3 --enable-auto-tool-choice --tool-call-parser qwen3_xml \
    > $OUT/logs/vllm_opt_$2.log 2>&1 &
  SOP=$!
  export TARGET_URL=http://127.0.0.1:$PT/v1 TARGET_MODEL=$1 OPT_URL=http://127.0.0.1:$PO/v1 OPT_MODEL=$OPT OPT_THINKING=1
  for p in $PT $PO; do
    for i in $(seq 1 240); do curl -sf localhost:$p/health >/dev/null && break; sleep 10; done
    curl -sf localhost:$p/health >/dev/null || { log "WK_ALF server $p failed ($2), see $OUT/logs"; return 1; }
  done
}
stop_servers() { kill $ST $SOP 2>/dev/null; wait $ST $SOP 2>/dev/null; sleep 10; }
trap stop_servers EXIT
new_ws() {  # <dir>
  [ -s $1/tasks.json ] && return
  cp $H/make_alf_tasks.py $WK/tools/make_alf_tasks.py
  $PY $WK/tools/new_ws.py $1 alf ${SMOKE:+--smoke $SMOKE} > /dev/null
}
evaluate() {  # <ws> <skill file|none> <out dir>
  [ -s $3/summary.json ] && return
  $PY $H/runner_alf.py $1 --eval $2 --out $3 --split test >> $OUT/logs/eval.log 2>&1
  log "wk_alf eval $(basename $3) rc=$? $(cat $3/summary.json 2>/dev/null | tr -d '\n ')"
}
log "WK_ALF start $R1-$R2 $SIZES${SMOKE:+ smoke=$SMOKE}"
for R in $(seq $R1 $R2); do
  for s in $SIZES; do
    tag=${s}_r$R${SMOKE:+_smoke}; ws=$OUT/$tag
    gpus_free
    start_servers ${HF[$s]} $tag || exit 1
    new_ws $ws
    if [ ! -f $ws/DONE ]; then
      log "wk_alf evolve $tag start"
      $PY $H/runner_alf.py $ws --iters ${ITERS:-8} > $OUT/logs/evolve_$tag.log 2>&1
      rc=$?; log "wk_alf evolve $tag rc=$rc $(grep '^done:' $OUT/logs/evolve_$tag.log)"
      [ $rc = 0 ] && $PY $WK/tools/export_skill.py $ws $ws/final_skills.md && date > $ws/DONE
    fi
    if [ -f $ws/DONE ]; then
      new_ws $OUT/eval_$tag
      evaluate $OUT/eval_$tag $ws/final_skills.md $OUT/test/$tag
      [ "$R" = 1 ] && evaluate $OUT/eval_$tag none $OUT/test/${s}_none
    fi
    stop_servers
  done
done
log "WK_ALF_DONE $R1-$R2 $SIZES"
