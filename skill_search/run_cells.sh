#!/usr/bin/env bash
# Run on the held GPU node:  run_cells.sh <MODEL_ID> <MAXNEW> <ids.json|all> <OUTDIR> skill1.md|none ...
# One vLLM process per GPU (4 shards), each loads the model once and runs every skill.
set -uo pipefail
KIT=$(cd "$(dirname "$0")/.." && pwd)
B=${VLLM_BUNDLE:?set VLLM_BUNDLE to a dir with .venv (vllm>=0.22) and hf_cache}
export MODEL_ID="$1" HF_HOME="$B/hf_cache" HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export PATH="$B/.venv/bin:$PATH"
MAXNEW="$2"; IDS="$3"; OUT="$4"; shift 4
TAG=$(basename "$MODEL_ID" | tr 'A-Z' 'a-z')
IDARG=(); [ "$IDS" != all ] && IDARG=(--ids "$IDS")
mkdir -p "$OUT" "$KIT/logs/vllm"
pids=()
for g in 0 1 2 3; do
  VLLM_CACHE_ROOT=/dev/shm/$USER-vllm-g$g TRITON_CACHE_DIR=/dev/shm/$USER-triton-g$g \
  CUDA_VISIBLE_DEVICES=$g "$B/.venv/bin/python" "$KIT/src/evaluate_vllm.py" \
    --skills "$@" "${IDARG[@]}" --max-new-tokens "$MAXNEW" --shard "$g/4" --out-dir "$OUT" \
    > "$KIT/logs/vllm/${TAG}_$(basename "$OUT")_$(basename "$IDS" .json)_g$g.log" 2>&1 &
  pids+=($!)
done
rc=0; for p in "${pids[@]}"; do wait "$p" || rc=1; done
echo "[run_cells] $TAG $(basename "$IDS") rc=$rc"; exit $rc
