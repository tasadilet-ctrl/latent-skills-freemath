#!/bin/bash
# Reordered 2026-11-18 (review advice: run the hand-written prompt check before tuning batches): wait for the
# running batch-100 training (train_rg.sh, PID given), then run_elim.sh, then resume run_bsweep.sh (it skips
# trained batch sizes and extracts their skills).   run_queue5.sh <train_rg pid>
set -uo pipefail
cd "$(dirname "$0")"
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
while kill -0 $1 2>/dev/null; do sleep 60; done
log "bsweep train b100 finished (driver stopped for reorder)"
log "QUEUE start: run_elim.sh"; bash run_elim.sh > queue_run_elim.log 2>&1; log "QUEUE done: run_elim.sh rc=$?"
log "QUEUE start: run_bsweep.sh (resume)"; bash run_bsweep.sh > queue_run_bsweep.log 2>&1; log "QUEUE done: run_bsweep.sh rc=$?"
