#!/usr/bin/env bash
# livemath_ts (new skill) on all 608 questions; compared with the refs in results_vllm/full.
KIT=$(cd "$(dirname "$0")/.." && pwd); R=$KIT/skill_search/run_cells.sh
for spec in "Qwen/Qwen3-8B 2048" "Qwen/Qwen3-14B 2048" "Qwen/Qwen3.6-27B 4096"; do
  set -- $spec
  bash $R "$1" "$2" all "$KIT/results_vllm/ts" $KIT/skills/livemath_ts.md
done
echo "[phase_ts] done"
