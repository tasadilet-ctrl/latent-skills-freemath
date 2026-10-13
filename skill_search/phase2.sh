#!/usr/bin/env bash
# Phase 2: chosen skill (proof_sketch) on held-out test + meta; then exploratory brief variant on dev.
KIT=$(cd "$(dirname "$0")/.." && pwd); S=$KIT/skills/search; R=$KIT/skill_search/run_cells.sh
for spec in "Qwen/Qwen3-8B 2048" "Qwen/Qwen3-14B 2048" "Qwen/Qwen3.6-27B 4096"; do
  set -- $spec
  bash $R "$1" "$2" "$KIT/skill_search/ids_test_meta.json" "$KIT/results_vllm/chosen" $S/proof_sketch.md
done
for spec in "Qwen/Qwen3-8B 2048" "Qwen/Qwen3-14B 2048" "Qwen/Qwen3.6-27B 4096"; do
  set -- $spec
  bash $R "$1" "$2" "$KIT/skill_search/ids_dev.json" "$KIT/results_vllm/explore" $S/proof_sketch_brief.md
done
echo "[phase2] done"
