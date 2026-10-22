#!/usr/bin/env bash
# After the mcqmath SkillOpt runs: PROTOCOL.md selection + test report, then the queued free-form runs.
set -uo pipefail
W=$HOME/skillopt_work
until grep -q "\[mqall\] ALL_DONE" $W/logs/mq_all.log 2>/dev/null; do
  tmux has-session -t mqfull 2>/dev/null || { echo "[after] mqfull gone without ALL_DONE, stopping"; exit 1; }
  sleep 120
done
source $W/gpu_wait.sh
GPU=1 $HOME/mcq_math/run_protocol_mq.sh 2>&1 | tee $W/logs/mq_protocol.log
$W/run_fm_next.sh
source $W/gpu_wait.sh
GPU=1 $W/kit_v4/freemath/run_protocol_fm.sh 2>&1 | tee $W/logs/fm_protocol.log
echo "[after] ALL_DONE"
