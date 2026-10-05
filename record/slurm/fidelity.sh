#!/bin/bash
#SBATCH --job-name=ls_fid
#SBATCH --output=/shared/home/adil.taibassarov/latent-skills/logs/fid_%j.out
#SBATCH -A issai
#SBATCH -p H100
#SBATCH -q issai-h100
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH -t 06:00:00
#SBATCH --exclude=g002,g006
#
#   MODEL_ID=Qwen/Qwen3-8B SKILL=compare_claims.md BASE=placebo_matched.md \
#     sbatch slurm/fidelity.sh vectors/<vec>.pt --probe livemath --bands ... --gammas ...
#
# BASE must match the --baseline-skill the vector was extracted against, or the
# steered arm starts from a different state than the subtraction was measured from.

set -euo pipefail
source /shared/home/adil.taibassarov/latent-skills/env.sh
mkdir -p "$TRITON_CACHE_DIR"
VEC="${1:?vectors path relative to LS_ROOT}"; shift
SKILL="${SKILL:-compare_claims.md}"
BASE="${BASE:-}"
EXTRA=()
[ -n "$BASE" ] && EXTRA=(--baseline-skill "$LS_ROOT/skills/$BASE")
echo "[job] node=$(hostname -s) model=$MODEL_ID vec=$VEC skill=$SKILL base=${BASE:-<none>}"
exec "$LS_PY" "$LS_ROOT/src/fidelity.py" --vectors "$LS_ROOT/$VEC" \
     --skill "$LS_ROOT/skills/$SKILL" "${EXTRA[@]}" "$@"
