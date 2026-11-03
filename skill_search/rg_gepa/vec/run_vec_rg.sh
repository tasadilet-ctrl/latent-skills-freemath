#!/usr/bin/env bash
# run_vec_rg.sh <gpu>: vector arm on the five GEPA skills (same worker rules as run_vec_posctl.sh)
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; GPU=$1
PY="$HOME/for Adilet/.venv/bin/python"; D=$HERE/out
export KIT=$HOME/vec_arm/kit HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
declare -A BS=([Qwen/Qwen3-8B]=48 [Qwen/Qwen3-14B]=32)
idle() { while [ "$(nvidia-smi -i $GPU --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' ')" -gt 2000 ]; do
  echo "[rgvec] GPU $GPU busy, waiting ($(date +%H:%M))"; sleep 120; done; }
step() { idle; echo "[rgvec] $B $(basename $M) $* ($(date +%H:%M))"
  (cd $HERE && CUDA_VISIBLE_DEVICES=$GPU MODEL_ID=$M "$PY" vec_rg.py "$@" --bench $B --out-dir $D)
  echo "[rgvec] $B $(basename $M) $1 ${3:-} rc=$?"; }
for MB in Qwen/Qwen3-8B:products Qwen/Qwen3-14B:products Qwen/Qwen3-14B:decimal_arithmetic Qwen/Qwen3-8B:polynomial_multiplication Qwen/Qwen3-8B:word_sorting; do
  M=${MB%%:*}; B=${MB##*:}; T=$(basename $M | tr A-Z a-z)
  ls $D/vectors/v_${T}_${B}_CONTROL.pt >/dev/null 2>&1 || step extract
  [ -f $D/fidelity_${T}_${B}.json ] || step fidelity
  for c in baseline text placebo B1 B2 CONTROL; do step eval --cond $c --max-new-tokens 2048 --batch-size ${BS[$M]}; done
  ~/rg_env/bin/python $HERE/rescore_rg.py $D > $HERE/vector_report.txt 2>&1
done
echo "[rgvec] ALL DONE"
