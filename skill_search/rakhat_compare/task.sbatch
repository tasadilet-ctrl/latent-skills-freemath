#!/bin/bash
#SBATCH -A issai
#SBATCH -p H100
#SBATCH -q issai-h100
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH -t 08:00:00
#SBATCH --exclude=g002,g004,g006
# usage: sbatch --array=0-N%C -J name --output=... task.sbatch <tasks.txt>
set -uo pipefail
B=/shared/home/adil.taibassarov/qwen_vllm_scripts_bundle_20260602
export PATH="$B/.venv/bin:$PATH" HF_HOME="$B/hf_cache" HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export VLLM_CACHE_ROOT=/dev/shm/$USER-vllm-$SLURM_JOB_ID TRITON_CACHE_DIR=/dev/shm/$USER-triton-$SLURM_JOB_ID
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
CMD=$(sed -n "$((SLURM_ARRAY_TASK_ID+1))p" "$1")
echo "[task] node=$(hostname -s) gpu=$CUDA_VISIBLE_DEVICES $CMD"
eval "$CMD"; rc=$?
rm -rf "$VLLM_CACHE_ROOT" "$TRITON_CACHE_DIR"
echo "[task] rc=$rc"; exit $rc
