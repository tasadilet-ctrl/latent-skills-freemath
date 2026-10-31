#!/usr/bin/env bash
# Dev stage of skill_search/budget/PROTOCOL.md: 4 drafts + 2 controls on every benchmark's dev split,
# Qwen3-8B / 14B / 3.6-27B, same stack as the main table. Baseline dev cells are reused from the
# protocol runs (same runner, same settings). Waits for an idle GPU (< 2 GB used) for every cell;
# finished cells are skipped by the runners, so a restart redoes only what is missing.
#   ./run_budget_dev.sh [dev|test] [skill.md ...]
set -uo pipefail
W=$HOME/skillopt_work; M=$HOME/mcq_math; B=$HOME/budget; PY=$W/vllm_env/bin/python
export PATH=$W/vllm_env/bin:$PATH HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
SPLIT=${1:-dev}; shift || true
SKILLS=${*:-$B/skills/route_first.md $B/skills/route_first_short.md $B/skills/small_cases.md $B/skills/check_answer.md $B/skills/brevity_control.md $M/skills/placebo_notation.md}
declare -A TOK=([Qwen/Qwen3-8B]=2048 [Qwen/Qwen3-14B]=2048 [Qwen/Qwen3.6-27B]=4096)
read -ra MODELS <<< "${MODELS:-Qwen/Qwen3-8B Qwen/Qwen3-14B Qwen/Qwen3.6-27B}"   # env MODELS splits work across cards
BENCHES=${BENCHES:-}   # env BENCHES limits this worker to those benchmarks
GPUS=${GPUS:-}   # env GPUS pins this worker to those cards (e.g. GPUS=1)
mkdir -p $B/results
pick_gpu() {
  while true; do
    while IFS=, read -r idx used; do
      idx=${idx// /}; [ -n "$GPUS" ] && [[ ",$GPUS," != *",$idx,"* ]] && continue
      [ "${used// /}" -le 2000 ] && { GPU_SEL=$idx; return; }
    done < <(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits)
    echo "[budget] waiting for an idle GPU ($(date +%H:%M))"; sleep 120
  done
}
for m in "${MODELS[@]}"; do
  for b in mmlupro_math_tq_sb supergpqa_math_hard; do
    [ -n "$BENCHES" ] && [[ " $BENCHES " != *" $b "* ]] && continue
    ids=$M/protocol/$b/ids_$([ $SPLIT = dev ] && echo val || echo test).json
    pick_gpu; echo "[budget] $b $SPLIT $m on GPU $GPU_SEL $(date +%H:%M)"
    CUDA_VISIBLE_DEVICES=$GPU_SEL VLLM_CACHE_ROOT=/dev/shm/$USER-budget$GPU_SEL MODEL_ID=$m $PY $M/evaluate_vllm_mcq.py \
      --data $M/data/$b.jsonl --ids $ids --tag $SPLIT --out-dir $B/results --max-new-tokens ${TOK[$m]} --skills $SKILLS
    rc=$?; echo "[budget] $b $SPLIT $m rc=$rc"
  done
  for b in beyondaime hardmath2 realmath imoanswer arxivmath; do
    [ -n "$BENCHES" ] && [[ " $BENCHES " != *" $b "* ]] && continue
    pick_gpu; echo "[budget] $b $SPLIT $m on GPU $GPU_SEL $(date +%H:%M)"
    CUDA_VISIBLE_DEVICES=$GPU_SEL VLLM_CACHE_ROOT=/dev/shm/$USER-budget$GPU_SEL MODEL_ID=$m $PY $W/kit_v4/freemath/evaluate_vllm_freemath.py \
      --items $W/fm_split/$b/$([ $SPLIT = dev ] && echo val || echo test)/items.json --bench $b --tag $SPLIT \
      --out-dir $B/results --max-new-tokens ${TOK[$m]} --skills $SKILLS
    rc=$?; echo "[budget] $b $SPLIT $m rc=$rc"
  done
done
echo "[budget] ${SPLIT}_DONE"
