#!/usr/bin/env bash
# PROTOCOL.md stage for the free-form SkillOpt runs: SkillOpt's seed + accepted skills are the drafts;
# dev (val) selection over Qwen3-8B / 14B / 3.6-27B with mcq_math/protocol_select.py; then test, once,
# on all three. Same stack for every cell: evaluate_vllm_freemath.py (kit prompt + forcing),
# 2048 new tokens (4096 for the 27B). No centroid rule: free-form questions have no options.
#
# The box is shared: each cell waits for an idle GPU (< 2 GB used, the kit's run.sh rule) and
# then uses it. Work is ordered model-outer (all 8B cells, then 14B, then 27B); finished cells
# are kept, so a restart redoes only what is missing.
#   ./run_protocol_fm.sh [bench:skillopt_model_tag ...]
#   default: beyondaime:qwen3-8b hardmath2:qwen3-8b realmath:qwen3-8b imoanswer:qwen3-8b arxivmath:qwen3-14b
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
W=$HOME/skillopt_work; PY=$W/vllm_env/bin/python; SEL=$HOME/mcq_math/protocol_select.py; SK=$HOME/mcq_math/skills
export PATH=$W/vllm_env/bin:$PATH HF_HUB_OFFLINE=1
RUNS=${*:-beyondaime:qwen3-8b hardmath2:qwen3-8b realmath:qwen3-8b imoanswer:qwen3-8b arxivmath:qwen3-14b}
declare -A TOK=([Qwen/Qwen3-8B]=2048 [Qwen/Qwen3-14B]=2048 [Qwen/Qwen3.6-27B]=4096)
declare -A NEED=([Qwen/Qwen3-8B]=26000 [Qwen/Qwen3-14B]=40000 [Qwen/Qwen3.6-27B]=72000)   # MiB incl. KV cache
MODELS=(Qwen/Qwen3-8B Qwen/Qwen3-14B Qwen/Qwen3.6-27B)

pick_gpu() {  # $1 = MiB needed; sets GPU_SEL and GPU_UTIL. Waits for an IDLE card (kit rule: never start
  # on a card someone else is using, > 2 GB). A card that merely had free memory once was not enough:
  # another user's training grew into it mid-cell and OOM-killed the 8B (2026-10-23).
  local need=$1 idx used total
  while true; do
    while IFS=, read -r idx used total; do
      used=${used// /}; total=${total// /}
      if [ "$used" -le 2000 ]; then
        GPU_SEL=${idx// /}; GPU_UTIL=0.90; return
      fi
    done < <(nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader,nounits)
    echo "[protofm] waiting for an idle GPU (need ${need} MiB; both cards busy, $(date +%H:%M))"; sleep 300
  done
}

run_cell() {  # model split bench drafts_dir skills...
  local m=$1 split=$2 b=$3 P=$4; shift 4
  pick_gpu ${NEED[$m]}
  echo "[protofm] $b $split $m on GPU $GPU_SEL (util $GPU_UTIL)"
  CUDA_VISIBLE_DEVICES=$GPU_SEL GPU_UTIL=$GPU_UTIL VLLM_CACHE_ROOT=/dev/shm/$USER-protofm$GPU_SEL \
    MODEL_ID=$m $PY $HERE/evaluate_vllm_freemath.py --items $W/fm_split/$b/$split/items.json --bench $b \
    --tag $([ $split = val ] && echo dev || echo test) --out-dir $P/results --max-new-tokens ${TOK[$m]} --skills "$@"
  echo "[protofm] $b $split $m rc=$?"
}

# drafts
for run in $RUNS; do
  b=${run%%:*}; t=${run##*:}; SO=$W/outputs/fm_${b}_${t}; P=$W/protocol_fm/$b; mkdir -p $P/drafts $P/results
  for f in $SO/skills/skill_v*.md $SO/best_skill.md; do
    [ -f "$f" ] || continue
    h=$(md5sum < "$f" | cut -c1-8); [ -n "$(ls $P/drafts/*_$h.md 2>/dev/null)" ] && continue
    cp "$f" "$P/drafts/$(basename "$f" .md)_$h.md"
  done
  echo "[protofm] $b drafts (from $t SkillOpt): $(ls $P/drafts | tr '\n' ' ')"
done
# dev, model-outer
for m in "${MODELS[@]}"; do for run in $RUNS; do
  b=${run%%:*}; P=$W/protocol_fm/$b
  run_cell $m val $b $P none $P/drafts/*.md
done; done
# selection
for run in $RUNS; do
  b=${run%%:*}; P=$W/protocol_fm/$b
  python3 $SEL select $P/results $b $P/drafts $P/chosen.md | tee $P/selection.txt
done
# test, once, model-outer
for m in "${MODELS[@]}"; do for run in $RUNS; do
  b=${run%%:*}; P=$W/protocol_fm/$b
  [ -f $P/chosen.md ] || { echo "[protofm] $b: no chosen draft"; continue; }
  run_cell $m test $b $P none $SK/placebo_matched.md $SK/strength_audit.md $SK/strength_audit_nometa.md $P/chosen.md
done; done
for run in $RUNS; do b=${run%%:*}; python3 $SEL report $W/protocol_fm/$b/results $b | tee $W/protocol_fm/$b/report.txt; done
echo "[protofm] ALL_DONE"
