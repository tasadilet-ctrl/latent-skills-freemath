#!/usr/bin/env bash
# ./run_vec_posctl.sh <gpu> <model> [bench ...]   (default benches: count mult)
# Same worker rules as vector_mcq/run_vec_mcq.sh: pinned to one card, waits until it is idle.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
GPU=$1; M=$2; shift 2; BENCHES=${*:-count mult}
PY="$HOME/for Adilet/.venv/bin/python"; D=$HOME/posctl/vec
export KIT=$HOME/vec_arm/kit HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
declare -A BS=([Qwen/Qwen3-8B]=48 [Qwen/Qwen3-14B]=32)
idle() { while [ "$(nvidia-smi -i $GPU --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' ')" -gt 2000 ]; do
  echo "[posvec] GPU $GPU busy, waiting ($(date +%H:%M))"; sleep 120; done; }
step() { idle; echo "[posvec] $B $(basename $M) $* on GPU $GPU ($(date +%H:%M))"
  CUDA_VISIBLE_DEVICES=$GPU MODEL_ID=$M "$PY" $HERE/vec_posctl.py "$@" --bench $B --out-dir $D
  local rc=$?; echo "[posvec] $B $(basename $M) $1 ${3:-} rc=$rc"; }
T=$(basename $M | tr A-Z a-z)
for B in $BENCHES; do
  ls $D/vectors/v_${T}_${B}_CONTROL.pt >/dev/null 2>&1 || step extract
  [ -f $D/fidelity_${T}_${B}.json ] || step fidelity
  for c in baseline text placebo B1 B2 CONTROL; do step eval --cond $c --max-new-tokens 2048 --batch-size ${BS[$M]}; done
done
echo "[posvec] $(basename $M) DONE"
