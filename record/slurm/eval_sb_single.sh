#!/bin/bash
#SBATCH --job-name=ls_sb1
#SBATCH --output=/shared/home/adil.taibassarov/latent-skills/logs/sb1_%j.out
#SBATCH -A issai
#SBATCH -p H100
#SBATCH -q issai-h100
#SBATCH --nodes=1
#SBATCH --gpus-per-node=4
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=256G
#SBATCH -t 12:00:00
#SBATCH --exclude=g002,g006
# Single-turn SpreadsheetBench. Unlike the agent harness this runs the model
# IN-PROCESS with batching, so the embed arm costs ~1h instead of ~25h through
# the serial hooked server.
set -euo pipefail
source /shared/home/adil.taibassarov/latent-skills/env.sh
COND="${1:?condition}"; VEC="${2:-}"; LAYERS="${3:-37}"; GAMMA="${4:-0.3}"
LIMIT="${LIMIT:-398}"; BS="${BS:-4}"; SKILL="${SKILL:-spreadsheet_edit.md}"
mkdir -p "$TRITON_CACHE_DIR"
echo "[job] $(hostname -s) model=$MODEL_ID single-turn/$COND vec=$VEC L$LAYERS g$GAMMA"
EXTRA=(); [ "$COND" = embed ] && EXTRA=(--vectors "$LS_ROOT/$VEC" --layers "$LAYERS" --gamma "$GAMMA")
PIDS=()
for i in 0 1 2 3; do
  CUDA_VISIBLE_DEVICES=$i "$LS_PY" "$LS_ROOT/src/evaluate_spreadsheet.py" \
      --condition "$COND" --limit "$LIMIT" --batch-size "$BS" \
      --skill "$LS_ROOT/skills/$SKILL" --shard "$i/4" "${EXTRA[@]}" \
      > "$LS_ROOT/logs/sb1_${SLURM_JOB_ID}_shard$i.log" 2>&1 &
  PIDS+=($!)
done
F=(); for i in 0 1 2 3; do wait "${PIDS[$i]}" || F+=("$i"); done
[ "${#F[@]}" -gt 0 ] && { echo "[job] SHARDS FAILED: ${F[*]}"; for i in "${F[@]}"; do tail -6 "$LS_ROOT/logs/sb1_${SLURM_JOB_ID}_shard$i.log"; done; exit 1; }
echo "[job] all 4 shards OK"
