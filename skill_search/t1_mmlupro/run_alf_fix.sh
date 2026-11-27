#!/bin/bash
# ALFWorld SkillOpt, fixed setup (2026-11-27). Same as run_alf.sh (Qwen3 4b/8b/14b players, Qwen3.6-27B editor, batch 40,
# 4 epochs, thinking on, T 1.0) with two changes:
#  1. SKILLOPT_HIDE_THINK=1: the editor sees actions + observations but not the player's thinking text. With thinking
#     shown, 8 failed games (~216k tokens) and the slow update (~740k) overflowed the editor's 131k context, so
#     failure reflection and the slow update almost never ran in run_alf.sh. Now ~13k / ~41k tokens.
#  2. Validation = all 140 valid_seen games (SkillOpt paper: 140 selection environments) instead of the repo's 18:
#     split data/alfworld_split_v140 (train 39 / val 140 / test 134, train and test unchanged).
# Test: each skill on its own model, the 134 valid_unseen games (alf_eval.sh), as before. Restartable.
#   run_alf_fix.sh <first run> <last run>
set -uo pipefail
cd "$(dirname "$0")"
W=$HOME/skillopt_work
export SKILLOPT_HIDE_THINK=1
mkdir -p skills_alf_fix
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
gpus_free() {
  while :; do
    n=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 <= 2000' | wc -l)
    [ "$n" -ge 2 ] && return; sleep 300
  done
}
log "ALF_FIX start $1-$2"
for R in $(seq $1 $2); do
  for s in 4b 8b 14b; do
    name=alf_fix_${s}_r$R; out=$W/outputs/$name
    if [ ! -s $out/summary.json ]; then
      gpus_free; log "alf_fix train $s r$R start"
      RUN_NAME=$name bash alf_train.sh $s $R env.split_dir=data/alfworld_split_v140 env.workers=48 env.max_api_workers=96 \
        >> train_driver.log 2>&1
      log "alf_fix train $s r$R rc=$?"
    fi
    [ -s $out/best_skill.md ] || { log "ALF_FIX_TRAIN_FAILED $s r$R"; continue; }
    grep -v "SLOW_UPDATE_\(START\|END\)" $out/best_skill.md > skills_alf_fix/${s}_r$R.md
    gpus_free; bash alf_eval.sh $s skills_alf_fix/${s}_r$R.md alf_fixtest_${s}_r$R 0 >> logs_alf_test.log 2>&1
    log "alf_fix test $s r$R rc=$?"
  done
  log "ALF_FIX_RUN_DONE r$R"
done
log "ALF_FIX_DONE $1-$2"
