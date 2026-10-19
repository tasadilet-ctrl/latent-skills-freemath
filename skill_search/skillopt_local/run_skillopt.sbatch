#!/bin/bash
#SBATCH -A issai
#SBATCH -p H100
#SBATCH -q issai-h100
#SBATCH --nodes=1
#SBATCH --gpus-per-node=2
#SBATCH --cpus-per-task=32
#SBATCH --mem=200G
#SBATCH -t 12:00:00
#SBATCH --exclude=g002,g006
#SBATCH --output=/shared/home/adil.taibassarov/skillopt_work/logs/%x_%j.out
# usage: sbatch -J name run_skillopt.sbatch <target model> <run name> [extra --cfg-options ...]
# SkillOpt as shipped (pinned commit 343db22), only the models are local:
# GPU0 = target (vLLM), GPU1 = optimizer Qwen3.6-27B (vLLM).
set -uo pipefail
W=/shared/home/adil.taibassarov/skillopt_work; B=/shared/home/adil.taibassarov/qwen_vllm_scripts_bundle_20260602
TARGET=$1; NAME=$2; shift 2
export HF_HOME=$B/hf_cache HF_HUB_OFFLINE=1 PATH=$B/.venv/bin:$PATH
PT=$((18000 + SLURM_JOB_ID % 1000)); PO=$((PT + 1))
echo "[job] node=$(hostname -s) target=$TARGET ports=$PT/$PO"
CUDA_VISIBLE_DEVICES=0 VLLM_CACHE_ROOT=/dev/shm/$USER-v0-$SLURM_JOB_ID $B/.venv/bin/vllm serve $TARGET \
  --port $PT --max-model-len 24576 --gpu-memory-utilization 0.9 --enable-prefix-caching \
  > $W/logs/${NAME}_target_$SLURM_JOB_ID.log 2>&1 &
CUDA_VISIBLE_DEVICES=1 VLLM_CACHE_ROOT=/dev/shm/$USER-v1-$SLURM_JOB_ID $B/.venv/bin/vllm serve Qwen/Qwen3.6-27B \
  --port $PO --max-model-len 131072 --gpu-memory-utilization 0.92 --enable-prefix-caching --max-num-seqs 32 --reasoning-parser qwen3 \
  > $W/logs/${NAME}_optimizer_$SLURM_JOB_ID.log 2>&1 &
for p in $PT $PO; do
  for i in $(seq 1 120); do curl -sf localhost:$p/health >/dev/null && break; sleep 10; done
  curl -sf localhost:$p/health >/dev/null || { echo "[job] server on $p failed"; exit 1; }
done
echo "[job] servers up"
export TARGET_QWEN_CHAT_BASE_URL=http://localhost:$PT/v1 TARGET_QWEN_CHAT_MODEL=$TARGET
export TARGET_QWEN_CHAT_THINKING_MODE=disabled TARGET_QWEN_CHAT_TEMPERATURE=0 TARGET_QWEN_CHAT_MAX_TOKENS=16384
export OPTIMIZER_QWEN_CHAT_BASE_URL=http://localhost:$PO/v1 OPTIMIZER_QWEN_CHAT_MODEL=Qwen/Qwen3.6-27B
export OPTIMIZER_QWEN_CHAT_THINKING_MODE=enabled OPTIMIZER_QWEN_CHAT_MAX_TOKENS=32768
export TARGET_QWEN_CHAT_TIMEOUT_SECONDS=900 OPTIMIZER_QWEN_CHAT_TIMEOUT_SECONDS=1800
cd $W/SkillOpt
.venv/bin/python scripts/train.py --config configs/livemathematicianbench/default.yaml \
  --target_backend qwen_chat --optimizer_backend qwen_chat \
  --target_model $TARGET --optimizer_model Qwen/Qwen3.6-27B \
  --cfg-options env.split_mode=split_dir env.split_dir=$W/lm_split env.out_root=$W/outputs/$NAME \
    env.exec_timeout=900 model.target_qwen_chat_thinking_mode=disabled model.optimizer_qwen_chat_thinking_mode=enabled "$@"
rc=$?; echo "[job] train rc=$rc"; kill %1 %2; exit $rc
