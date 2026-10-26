#!/usr/bin/env bash
# Vector arm of livemath_ts on the MCQ benchmarks (see vec_mcq.py for the design).
#   ./run_vec_mcq.sh <gpu> <bench> [model ...]       default models: Qwen/Qwen3-8B Qwen/Qwen3-14B
# One worker per GPU: the worker is pinned to its card and waits until the card is idle
# (< 2 GB used, the kit's rule) before every step, so two workers never race for one card
# and nobody else's job is crowded out. Finished cells are skipped on a restart.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
GPU=$1; B=$2; shift 2
MODELS=${*:-Qwen/Qwen3-8B Qwen/Qwen3-14B}
PY="$HOME/for Adilet/.venv/bin/python"; D=$HOME/vec_arm
export KIT=$D/kit HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
declare -A TOK=([Qwen/Qwen3-8B]=2048 [Qwen/Qwen3-14B]=2048 [Qwen/Qwen3.6-27B]=4096)
declare -A BS=([Qwen/Qwen3-8B]=48 [Qwen/Qwen3-14B]=32 [Qwen/Qwen3.6-27B]=16)
idle() { while [ "$(nvidia-smi -i $GPU --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' ')" -gt 2000 ]; do
  echo "[vecarm] GPU $GPU busy, waiting ($(date +%H:%M))"; sleep 300; done; }
step() { idle; echo "[vecarm] $B $(basename $M) $* on GPU $GPU ($(date +%H:%M))"
  CUDA_VISIBLE_DEVICES=$GPU MODEL_ID=$M "$PY" $HERE/vec_mcq.py "$@" --bench $B --out-dir $D
  local rc=$?     # read first: a $(...) in the echo below would reset $? to 0
  echo "[vecarm] $B $(basename $M) $1 ${3:-} rc=$rc"; }
for M in $MODELS; do
  T=$(basename $M | tr A-Z a-z)
  ls $D/vectors/v_${T}_${B}_CONTROL.pt >/dev/null 2>&1 || step extract
  [ -f $D/fidelity_${T}_${B}.json ] || step fidelity
  for c in ${CONDS:-baseline text placebo B1 B2 CONTROL}; do     # CONDS splits one model over two cards
    step eval --cond $c --max-new-tokens ${TOK[$M]} --batch-size ${BS[$M]}
  done
done
echo "[vecarm] $B DONE"
