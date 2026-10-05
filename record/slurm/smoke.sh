#!/bin/bash
#SBATCH --job-name=ls_smoke
#SBATCH --output=/shared/home/adil.taibassarov/latent-skills/logs/smoke_%j.out
#SBATCH -A issai
#SBATCH -p H100
#SBATCH -q issai-h100
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH -t 01:00:00
#SBATCH --exclude=g002
set -euo pipefail
source /shared/home/adil.taibassarov/latent-skills/env.sh
mkdir -p "$TRITON_CACHE_DIR"
echo "[job] node=$(hostname -s)"; nvidia-smi -L
exec "$LS_PY" "$LS_ROOT/src/smoke_test.py"
