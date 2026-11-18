#!/bin/bash
# After run_queue2.sh (T2 runs 2-5) exits and both GPUs are free: the Reasoning Gym batch-size sweep.
set -uo pipefail
cd "$(dirname "$0")"
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
while pgrep -u "$USER" -f "bash run_queue2.sh" >/dev/null; do sleep 300; done
while [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 <= 2000' | wc -l)" -lt 2 ]; do sleep 300; done
log "QUEUE start: run_bsweep.sh"; bash run_bsweep.sh > queue_run_bsweep.log 2>&1; log "QUEUE done: run_bsweep.sh rc=$?"
