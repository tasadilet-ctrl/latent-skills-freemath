#!/usr/bin/env bash
# PROTOCOL.md stage for the free-form SkillOpt runs: SkillOpt's seed + accepted skills are the drafts;
# dev (val) selection over Qwen3-8B / 14B / 3.6-27B with mcq_math/protocol_select.py; then test, once,
# on all three. Same stack for every cell: evaluate_vllm_freemath.py (kit prompt + forcing),
# 2048 new tokens (4096 for the 27B). No centroid rule: free-form questions have no options.
#   ./run_protocol_fm.sh [bench:skillopt_model_tag ...]
#   default: beyondaime:qwen3-8b hardmath2:qwen3-8b realmath:qwen3-8b imoanswer:qwen3-8b arxivmath:qwen3-14b
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
W=$HOME/skillopt_work; PY=$W/vllm_env/bin/python; SEL=$HOME/mcq_math/protocol_select.py; SK=$HOME/mcq_math/skills
export PATH=$W/vllm_env/bin:$PATH HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES=${GPU:-1} VLLM_CACHE_ROOT=/dev/shm/$USER-proto
RUNS=${*:-beyondaime:qwen3-8b hardmath2:qwen3-8b realmath:qwen3-8b imoanswer:qwen3-8b arxivmath:qwen3-14b}
declare -A TOK=([Qwen/Qwen3-8B]=2048 [Qwen/Qwen3-14B]=2048 [Qwen/Qwen3.6-27B]=4096)
MODELS=(Qwen/Qwen3-8B Qwen/Qwen3-14B Qwen/Qwen3.6-27B)
for run in $RUNS; do
  b=${run%%:*}; t=${run##*:}
  SO=$W/outputs/fm_${b}_${t}; P=$W/protocol_fm/$b; mkdir -p $P/drafts $P/results
  [ -f $SO/summary.json ] || [ -f $SO/best_skill.md ] || { echo "[protofm] $b: no SkillOpt run in $SO, skipping"; continue; }
  for f in $SO/skills/skill_v*.md $SO/best_skill.md; do
    [ -f "$f" ] || continue
    h=$(md5sum < "$f" | cut -c1-8); [ -n "$(ls $P/drafts/*_$h.md 2>/dev/null)" ] && continue
    cp "$f" "$P/drafts/$(basename "$f" .md)_$h.md"
  done
  echo "[protofm] $b drafts (from $t SkillOpt): $(ls $P/drafts | tr '\n' ' ')"
  for m in "${MODELS[@]}"; do
    MODEL_ID=$m $PY $HERE/evaluate_vllm_freemath.py --items $W/fm_split/$b/val/items.json --bench $b --tag dev \
      --out-dir $P/results --max-new-tokens ${TOK[$m]} --skills none $P/drafts/*.md
    echo "[protofm] $b dev $m rc=$?"
  done
  python3 $SEL select $P/results $b $P/drafts $P/chosen.md | tee $P/selection.txt
  [ -f $P/chosen.md ] || { echo "[protofm] $b: no chosen draft"; continue; }
  for m in "${MODELS[@]}"; do
    MODEL_ID=$m $PY $HERE/evaluate_vllm_freemath.py --items $W/fm_split/$b/test/items.json --bench $b --tag test \
      --out-dir $P/results --max-new-tokens ${TOK[$m]} \
      --skills none $SK/placebo_matched.md $SK/strength_audit.md $SK/strength_audit_nometa.md $P/chosen.md
    echo "[protofm] $b test $m rc=$?"
  done
  python3 $SEL report $P/results $b | tee $P/report.txt
done
echo "[protofm] ALL_DONE"
