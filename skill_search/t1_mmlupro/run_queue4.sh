#!/bin/bash
# After run_queue3.sh (Reasoning Gym batch sweep) exits: the option-elimination prompt column on T1 MMLU-Pro.
set -uo pipefail
cd "$(dirname "$0")"
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
while pgrep -u "$USER" -f "bash run_queue3.sh" >/dev/null; do sleep 300; done
log "QUEUE start: run_elim.sh"; bash run_elim.sh > queue_run_elim.log 2>&1; log "QUEUE done: run_elim.sh rc=$?"
