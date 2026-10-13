#!/usr/bin/env bash
# Phase 1: reference cells on all 608 + the drafts on dev only, all three models.
KIT=$(cd "$(dirname "$0")/.." && pwd); S=$KIT/skills; R=$KIT/skill_search/run_cells.sh
DRAFTS="$S/search/clause_audit.md $S/search/proof_sketch.md $S/search/blind_first.md"
REFS="none $S/placebo_matched.md $S/strength_audit.md $S/strength_audit_nometa.md"
for spec in "Qwen/Qwen3-8B 2048" "Qwen/Qwen3-14B 2048" "Qwen/Qwen3.6-27B 4096"; do
  set -- $spec
  bash $R "$1" "$2" "$KIT/skill_search/ids_dev.json" "$KIT/results_vllm/drafts" $DRAFTS
  bash $R "$1" "$2" all "$KIT/results_vllm/full" $REFS
done
echo "[phase1] done"
