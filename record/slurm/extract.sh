#!/bin/bash
#SBATCH --job-name=ls_extract
#SBATCH --output=/shared/home/adil.taibassarov/latent-skills/logs/extract_%j.out
#SBATCH -A issai
#SBATCH -p H100
#SBATCH -q issai-h100
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH -t 02:00:00
#SBATCH --exclude=g002,g006
# g002's munge auth died 2026-08-14; SLURM still reports it IDLE. Never schedule there.
# g006 runs jobs that hold GPU memory without requesting it through gres.
#
#   MODEL_ID=Qwen/Qwen3-8B SKILL=compare_claims.md \
#     sbatch slurm/extract.sh neutral 50 placebo_matched.md
#
# Third argument is the system prompt to CONTRAST AGAINST. Omit it and the
# contrast is against no system message at all -- the two extraction arms.

set -euo pipefail
source /shared/home/adil.taibassarov/latent-skills/env.sh
POOL="${1:-neutral}"
N="${2:-50}"
BASE="${3:-}"   # space-separated list allowed -> contrast against their mean
SKILL="${SKILL:-compare_claims.md}"
SKILLPOS="${SKILLPOS:-system}"   # system | user
mkdir -p "$TRITON_CACHE_DIR"
echo "[job] node=$(hostname -s) model=$MODEL_ID pool=$POOL n=$N skill=$SKILL base=${BASE:-<none>}"
nvidia-smi -L
EXTRA=()
if [ -n "$BASE" ]; then
  EXTRA=(--baseline-skill)
  for b in $BASE; do EXTRA+=("$LS_ROOT/skills/$b"); done
fi
exec "$LS_PY" "$LS_ROOT/src/extract_vectors.py" \
     --pool "$POOL" --n "$N" --skill "$LS_ROOT/skills/$SKILL" \
     --skill-position "$SKILLPOS" "${EXTRA[@]}"
