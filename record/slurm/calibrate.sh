#!/bin/bash
#SBATCH --job-name=ls_calib
#SBATCH --output=/shared/home/adil.taibassarov/latent-skills/logs/calib_%j.out
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
set -euo pipefail
source /shared/home/adil.taibassarov/latent-skills/env.sh
mkdir -p "$TRITON_CACHE_DIR"
VEC="${1:?vectors path relative to LS_ROOT}"; shift
echo "[job] node=$(hostname -s) vec=$VEC"
exec "$LS_PY" "$LS_ROOT/src/calibrate.py" --vectors "$LS_ROOT/$VEC" "$@"
