#!/bin/bash
# Goal (2026-11-23): show a text skill beats no skill on a maths benchmark, with a placebo control.
# Waits for "SG_DONE 1-1" (run_sg.sh), then:
#  A. LiveMath option 1 (Adil's setup), Qwen3-4B: finish runs 4-5 (train_lm.sh + test none/own skill), then a
#     length-matched placebo for each run's skill (make_placebo.py) tested at that run's seed -> results_lm/r<R>/.
#  B. MMLU-Pro T2 test (255 q), all 4 models, 5 runs (seed = run): no skill, the elimination prompt and a
#     placebo of the same length, answered in the same process -> results_ctl/r<R>/.
set -uo pipefail
cd "$(dirname "$0")"; H=$(pwd)
W=$HOME/skillopt_work; PY=$W/vllm_env/bin/python
MQ=$HOME/mcq_math/data/mmlupro_math_tq_sb.jsonl; LM=$HOME/mcq_math/data/livemath556.jsonl
declare -A HF=([4b]=Qwen/Qwen3-4B [8b]=Qwen/Qwen3-8B [14b]=Qwen/Qwen3-14B [27b]=Qwen/Qwen3.6-27B)
declare -A TOK=([4b]=2048 [8b]=2048 [14b]=2048 [27b]=4096)
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
gpus_free() {
  while :; do
    n=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 <= 2000' | wc -l)
    [ "$n" -ge 2 ] && return; sleep 300
  done
}
ev() {  # <size> <gpu> <data> <seed> <out dir> <log> <skills...>
  local s=$1 g=$2 d=$3 sd=$4 o=$5 lg=$6; shift 6
  CUDA_VISIBLE_DEVICES=$g VLLM_CACHE_ROOT=/dev/shm/$USER-q7-$g HF_HUB_OFFLINE=1 PATH=$W/vllm_env/bin:$PATH \
  MODEL_ID=${HF[$s]} $PY evaluate_mcq_t1.py --data $d --skills "$@" --temperature 1.0 --seed $sd \
    --attention-backend FLASHINFER --max-model-len 16384 --max-new-tokens ${TOK[$s]} --out-dir $o > $lg 2>&1
}
until grep -q "SG_DONE 1-1" jobs.txt; do sleep 600; done
log "QUEUE7 start"
# ---- A
for R in 4 5; do
  out=$W/outputs/lm_t1_4b_r$R
  if [ ! -s $out/summary.json ]; then
    gpus_free; log "q7 A train 4b r$R start"
    RUN_NAME=lm_t1_4b_r$R bash train_lm.sh 4b $R >> train_driver.log 2>&1; log "q7 A train 4b r$R rc=$?"
  fi
  [ -s $out/best_skill.md ] || { log "q7 A no skill r$R"; continue; }
  grep -v "SLOW_UPDATE_\(START\|END\)" $out/best_skill.md > skills_lm/4b_r$R.md
  gpus_free; ev 4b 0 $LM $R results_lm/r$R logs_lm_test_r$R.log none skills_lm/4b_r$R.md; log "q7 A test 4b r$R rc=$?"
done
for R in 1 2 3 4 5; do
  [ -s skills_lm/4b_r$R.md ] || continue
  python3 make_placebo.py skills_lm/4b_r$R.md skills_lm/placebo_r$R.md >> logs_lm_setup.log
done
gpus_free
( for R in 1 3 5; do [ -s skills_lm/placebo_r$R.md ] && ev 4b 0 $LM $R results_lm/r$R logs_lm_plc_r$R.log skills_lm/placebo_r$R.md; log "q7 A placebo r$R rc=$?"; done ) &
( for R in 2 4; do [ -s skills_lm/placebo_r$R.md ] && ev 4b 1 $LM $R results_lm/r$R logs_lm_plc_r$R.log skills_lm/placebo_r$R.md; log "q7 A placebo r$R rc=$?"; done ) &
wait
# ---- B
mkdir -p skills_ctl results_ctl
cp skills_t3/initial_elim.md skills_ctl/elim.md
python3 make_placebo.py skills_ctl/elim.md skills_ctl/placebo.md >> logs_lm_setup.log
for R in 1 2 3 4 5; do
  gpus_free; log "q7 B r$R start"
  ( ev 27b 0 $MQ $R results_ctl/r$R logs_ctl_27b_r$R.log none skills_ctl/elim.md skills_ctl/placebo.md; log "q7 B 27b r$R rc=$?"
    ev 4b 0 $MQ $R results_ctl/r$R logs_ctl_4b_r$R.log none skills_ctl/elim.md skills_ctl/placebo.md; log "q7 B 4b r$R rc=$?" ) &
  ( ev 14b 1 $MQ $R results_ctl/r$R logs_ctl_14b_r$R.log none skills_ctl/elim.md skills_ctl/placebo.md; log "q7 B 14b r$R rc=$?"
    ev 8b 1 $MQ $R results_ctl/r$R logs_ctl_8b_r$R.log none skills_ctl/elim.md skills_ctl/placebo.md; log "q7 B 8b r$R rc=$?" ) &
  wait
done
log "QUEUE7_DONE"
