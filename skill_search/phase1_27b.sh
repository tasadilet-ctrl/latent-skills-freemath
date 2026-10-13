#!/usr/bin/env bash
KIT=$(cd "$(dirname "$0")/.." && pwd); S=$KIT/skills; R=$KIT/skill_search/run_cells.sh
bash $R Qwen/Qwen3.6-27B 4096 "$KIT/skill_search/ids_dev.json" "$KIT/results_vllm/drafts" $S/search/clause_audit.md $S/search/proof_sketch.md $S/search/blind_first.md
bash $R Qwen/Qwen3.6-27B 4096 all "$KIT/results_vllm/full" none $S/placebo_matched.md $S/strength_audit.md $S/strength_audit_nometa.md
echo "[phase1_27b] done"
