#!/bin/bash
# Queue, reordered on 2026-11-16 after run_hints.sh failed at start-up (vLLM max_num_seqs, fixed in
# gen_hints.py): wait for the running run_rg.sh, then run_hints.sh, run_gepa_t2.sh, run_t2.sh 2 5.
set -uo pipefail
cd "$(dirname "$0")"
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
gpus_free() {
  while :; do
    n=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 <= 2000' | wc -l)
    [ "$n" -ge 2 ] && return; sleep 300
  done
}
while pgrep -u "$USER" -f "bash run_rg.sh" >/dev/null; do sleep 120; done
for step in "run_hints.sh" "run_gepa_t2.sh" "run_t2.sh 2 5"; do
  gpus_free; log "QUEUE start: $step"
  bash $step > queue_$(echo $step | tr ' .' '__').log 2>&1
  log "QUEUE done: $step rc=$?"
done
log "QUEUE_ALL_DONE"
