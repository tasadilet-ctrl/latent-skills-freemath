#!/usr/bin/env bash
# livemath_ts_meta (livemath_ts + the meta-option rule) on every benchmark's TEST split, 3 models,
# same stack as the PROTOCOL.md tables: MCQ via evaluate_vllm_mcq.py, free-form via
# evaluate_vllm_freemath.py (kit prompt + forcing; 2048 tokens, 4096 for the 27B). None of these
# benchmarks has a meta-option, so if the skill's LiveMath gain was only the loophole it should
# match plain livemath_ts here. Waits for an idle GPU per cell; shares the box with run_ts_fm.sh.
set -uo pipefail
W=$HOME/skillopt_work; M=$HOME/mcq_math; PY=$W/vllm_env/bin/python; SK=$M/skills/livemath_ts_meta.md
export PATH=$W/vllm_env/bin:$PATH HF_HUB_OFFLINE=1
declare -A TOK=([Qwen/Qwen3-8B]=2048 [Qwen/Qwen3-14B]=2048 [Qwen/Qwen3.6-27B]=4096)
MODELS=(Qwen/Qwen3-8B Qwen/Qwen3-14B Qwen/Qwen3.6-27B)
pick_gpu() {
  while true; do
    while IFS=, read -r idx used; do
      [ "${used// /}" -le 2000 ] && { GPU_SEL=${idx// /}; return; }
    done < <(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits)
    echo "[tsmeta] waiting for an idle GPU ($(date +%H:%M))"; sleep 120
  done
}
for m in "${MODELS[@]}"; do
  for b in mmlupro_math_tq_sb supergpqa_math_hard; do
    P=$M/protocol/$b; pick_gpu; echo "[tsmeta] $b test $m on GPU $GPU_SEL"
    CUDA_VISIBLE_DEVICES=$GPU_SEL VLLM_CACHE_ROOT=/dev/shm/$USER-tsmeta$GPU_SEL MODEL_ID=$m $PY $M/evaluate_vllm_mcq.py \
      --data $M/data/$b.jsonl --ids $P/ids_test.json --tag test --out-dir $P/results --max-new-tokens ${TOK[$m]} --skills $SK
    echo "[tsmeta] $b test $m rc=$?"
  done
  for b in beyondaime hardmath2 realmath imoanswer arxivmath; do
    P=$W/protocol_fm/$b; pick_gpu; echo "[tsmeta] $b test $m on GPU $GPU_SEL"
    CUDA_VISIBLE_DEVICES=$GPU_SEL VLLM_CACHE_ROOT=/dev/shm/$USER-tsmeta$GPU_SEL MODEL_ID=$m $PY $W/kit_v4/freemath/evaluate_vllm_freemath.py \
      --items $W/fm_split/$b/test/items.json --bench $b --tag test --out-dir $P/results --max-new-tokens ${TOK[$m]} --skills $SK
    echo "[tsmeta] $b test $m rc=$?"
  done
done
echo "[tsmeta] ALL_DONE"
