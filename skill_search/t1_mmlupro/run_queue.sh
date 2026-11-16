#!/bin/bash
# The queue agreed on 2026-11-16, run in order, each step after both GPUs are free (<= 2 GB used):
#   1 run_hints.sh   2 run_rg.sh   3 run_gepa_t2.sh   4 run_t2.sh 2 5 (resume T2)
# A failed step is logged and the queue moves on.     nohup bash run_queue.sh > queue.log 2>&1 &
set -uo pipefail
cd "$(dirname "$0")"
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
gpus_free() {
  while :; do
    n=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 <= 2000' | wc -l)
    [ "$n" -ge 2 ] && return; sleep 300
  done
}
for step in "run_hints.sh" "run_rg.sh" "run_gepa_t2.sh" "run_t2.sh 2 5"; do
  gpus_free; log "QUEUE start: $step"
  bash $step > queue_$(echo $step | tr ' .' '__').log 2>&1
  log "QUEUE done: $step rc=$?"
done
log "QUEUE_ALL_DONE"
