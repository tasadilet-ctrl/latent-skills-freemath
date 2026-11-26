#!/bin/bash
# ALFWorld, SkillOpt vs no skill for Qwen3 4B/8B/14B (2026-11-25), the WikiSkill paper's Table 1 ALFWorld column for
# SkillOpt only. No-skill baselines: alf_base_<size>_think_s1 (alf_eval.sh, thinking on). Per run R (1-3): SkillOpt
# for 4b 8b 14b (alf_train.sh: SkillOpt's ALFWorld config, batch 40 = all 39 training games, 4 epochs, starting
# skill = SkillOpt's ALFWorld initial skill, Qwen3.6-27B edits), then the run's skill on its own model on the 134 test
# games (alf_eval.sh). Restartable.   run_alf.sh <first run> <last run>
set -uo pipefail
cd "$(dirname "$0")"
W=$HOME/skillopt_work
mkdir -p skills_alf
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
gpus_free() {
  while :; do
    n=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 <= 2000' | wc -l)
    [ "$n" -ge 2 ] && return; sleep 300
  done
}
log "ALF start $1-$2"
if [ ! -s $W/outputs/alf_base_14b_think_s1/eval_summary.json ]; then
  gpus_free; bash alf_eval.sh 14b skills_alf/none.md alf_base_14b_think_s1 0 >> logs_alf_base_14b_think.log 2>&1
  log "alf base 14b rc=$?"
fi
for R in $(seq $1 $2); do
  for s in 4b 8b 14b; do
    out=$W/outputs/alf_${s}_r$R
    if [ ! -s $out/summary.json ]; then
      gpus_free; log "alf train $s r$R start"
      bash alf_train.sh $s $R >> train_driver.log 2>&1; log "alf train $s r$R rc=$?"
    fi
    [ -s $out/best_skill.md ] || { log "ALF_TRAIN_FAILED $s r$R"; continue; }
    grep -v "SLOW_UPDATE_\(START\|END\)" $out/best_skill.md > skills_alf/${s}_r$R.md
    gpus_free; bash alf_eval.sh $s skills_alf/${s}_r$R.md alf_test_${s}_r$R 0 >> logs_alf_test.log 2>&1
    log "alf test $s r$R rc=$?"
  done
  log "ALF_RUN_DONE r$R"
done
log "ALF_DONE $1-$2"
