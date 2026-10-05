#!/bin/bash
#SBATCH --job-name=ls_sb
#SBATCH --output=/shared/home/adil.taibassarov/latent-skills/logs/sb_%j.out
#SBATCH -A issai
#SBATCH -p H100
#SBATCH -q issai-h100
#SBATCH --nodes=1
#SBATCH --gpus-per-node=4
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=256G
#SBATCH -t 20:00:00
#SBATCH --exclude=g002,g006
#
#   MODEL_ID=Qwen/Qwen3-8B sbatch slurm/eval_sb.sh baseline
#   MODEL_ID=Qwen/Qwen3-8B SKILL=spreadsheet_edit.md sbatch slurm/eval_sb.sh text
#   MODEL_ID=Qwen/Qwen3-8B sbatch slurm/eval_sb.sh embed vectors/<vec>.pt 34 0.3

set -euo pipefail
source /shared/home/adil.taibassarov/latent-skills/env.sh
COND="${1:?condition}"; VEC="${2:-}"; LAYERS="${3:-34}"; GAMMA="${4:-0.3}"
LIMIT="${LIMIT:-400}"; BS="${BS:-4}"; SKILL="${SKILL:-spreadsheet_edit.md}"
MAXNEW="${MAXNEW:-1536}"
mkdir -p "$TRITON_CACHE_DIR"
echo "[job] node=$(hostname -s) model=$MODEL_ID spreadsheet/$COND skill=$SKILL vec=$VEC"
EXTRA=()
[ "$COND" = "embed" ] && EXTRA=(--vectors "$LS_ROOT/$VEC" --layers "$LAYERS" --gamma "$GAMMA")
for i in 0 1 2 3; do
  CUDA_VISIBLE_DEVICES=$i "$LS_PY" "$LS_ROOT/src/evaluate_spreadsheet.py" \
      --condition "$COND" --limit "$LIMIT" --batch-size "$BS" \
      --max-new-tokens "$MAXNEW" --skill "$LS_ROOT/skills/$SKILL" \
      --shard "$i/4" "${EXTRA[@]}" \
      > "$LS_ROOT/logs/sb_${SLURM_JOB_ID}_shard$i.log" 2>&1 &
done
wait
echo "[job] shards done"; tail -n 24 "$LS_ROOT/logs/sb_${SLURM_JOB_ID}_shard0.log"
