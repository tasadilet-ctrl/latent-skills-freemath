#!/bin/bash
# Test of the acceptance check (noise fix): run 1 again with 4 samples per validation question
# (MCQKIT_VAL_REPEATS=4, patch_valrep.py); everything else as run_t1.sh. Then test the 4 new skills on all
# 4 models with seed 1 (baseline = run 1's). Outputs: outputs/mq_t1v4_<size>_r1, skills/v4_<size>_r1.md,
# results/r1/..._v4_<size>_r1_s0of1.json. Restartable.   run_valrep.sh   (from ~/t1_mq)
set -uo pipefail
cd "$(dirname "$0")"
W=$HOME/skillopt_work; PY=$W/vllm_env/bin/python; DATA=$HOME/mcq_math/data/mmlupro_math_tq_sb.jsonl; R=1
declare -A HF=([4b]=Qwen/Qwen3-4B [8b]=Qwen/Qwen3-8B [14b]=Qwen/Qwen3-14B [27b]=Qwen/Qwen3.6-27B)
declare -A TOK=([4b]=2048 [8b]=2048 [14b]=2048 [27b]=4096)
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
gpus_free() {
  while :; do
    n=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 <= 2000' | wc -l)
    [ "$n" -ge 2 ] && return; sleep 300
  done
}
export MCQKIT_VAL_REPEATS=4
for s in 27b 14b 8b 4b; do
  out=$W/outputs/mq_t1v4_${s}_r$R
  if [ ! -s $out/summary.json ]; then
    gpus_free; log "train v4 $s r$R start"
    RUN_NAME=mq_t1v4_${s}_r$R bash train_one.sh $s $R >> train_driver.log 2>&1; log "train v4 $s r$R rc=$?"
  fi
  [ -s $out/best_skill.md ] || { log "TRAIN_FAILED v4 $s r$R"; exit 1; }
  grep -v "SLOW_UPDATE_\(START\|END\)" $out/best_skill.md > skills/v4_${s}_r$R.md
done
unset MCQKIT_VAL_REPEATS
one() {  # <size> <gpu>
  local s=$1 g=$2 tag; tag=$(basename ${HF[$s]} | tr A-Z a-z)
  [ -s results/r$R/mmlupro_math_tq_sb_${tag}_v4_27b_r${R}_s0of1.json ] && return 0
  CUDA_VISIBLE_DEVICES=$g VLLM_CACHE_ROOT=/dev/shm/$USER-t1-ev$g HF_HUB_OFFLINE=1 PATH=$W/vllm_env/bin:$PATH \
  MODEL_ID=${HF[$s]} $PY evaluate_mcq_t1.py --data $DATA \
    --skills skills/v4_4b_r$R.md skills/v4_8b_r$R.md skills/v4_14b_r$R.md skills/v4_27b_r$R.md \
    --temperature 1.0 --seed $R --attention-backend FLASHINFER --max-model-len 16384 \
    --max-new-tokens ${TOK[$s]} --out-dir results/r$R > logs_test_v4_${s}_r$R.log 2>&1
  log "test v4 $s r$R rc=$?"
}
gpus_free; log "test v4 r$R start"
( one 27b 0; one 4b 0 ) &
( one 14b 1; one 8b 1 ) &
wait
log "VALREP_DONE"
