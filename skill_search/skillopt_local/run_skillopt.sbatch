#!/bin/bash
#SBATCH -A issai
#SBATCH -p H100
#SBATCH -q issai-h100
#SBATCH --nodes=1
#SBATCH --gpus-per-node=2
#SBATCH --cpus-per-task=32
#SBATCH --mem=200G
#SBATCH -t 12:00:00
#SBATCH --exclude=g002,g004,g006
# Run SkillOpt (setup.sh installs it, pinned at 343db22) with two local vLLM servers:
#   GPU0 = target model (the model the skill is written for), thinking off
#   GPU1 = optimizer Qwen3.6-27B (reads trajectories, writes the edits), thinking on
#
# usage: sbatch -J <run name> --output=<log> run_skillopt.sbatch <config> <target model> <split dir> [--cfg-options ...]
#   <config>     SkillOpt config, relative to the SkillOpt checkout, e.g.
#                configs/livemathematicianbench/default.yaml
#   <split dir>  folder with train/ val/ test/ in the benchmark loader's format
#                (LiveMath: make_split.py)
#   extra args   passed to SkillOpt's --cfg-options, e.g. train.num_epochs=2
# The run lands in $SKILLOPT_WORK/outputs/<run name>/ (best_skill.md, summary.json, ...).
#
# Environment (defaults are this cluster's):
#   SKILLOPT_WORK    work dir from setup.sh                 ($HOME/skillopt_work)
#   VLLM_ENV         venv with vllm and the HF cache next to it
#   OPTIMIZER        optimizer model                         (Qwen/Qwen3.6-27B)
#   TARGET_MAX_LEN   target context; raise for long-context benchmarks (24576)
set -uo pipefail
W=${SKILLOPT_WORK:-$HOME/skillopt_work}
B=${VLLM_ENV:-/shared/home/adil.taibassarov/qwen_vllm_scripts_bundle_20260602}
OPT=${OPTIMIZER:-Qwen/Qwen3.6-27B}
CONFIG=$1; TARGET=$2; SPLIT=$(realpath "$3"); shift 3
NAME=${SLURM_JOB_NAME:-skillopt}
export HF_HOME=$B/hf_cache HF_HUB_OFFLINE=1 PATH=$B/.venv/bin:$PATH   # ninja for torch.compile comes from this PATH
mkdir -p "$W/logs"
PT=$((18000 + SLURM_JOB_ID % 1000)); PO=$((PT + 1))
echo "[job] node=$(hostname -s) config=$CONFIG target=$TARGET split=$SPLIT ports=$PT/$PO"
CUDA_VISIBLE_DEVICES=0 VLLM_CACHE_ROOT=/dev/shm/$USER-v0-$SLURM_JOB_ID $B/.venv/bin/vllm serve $TARGET \
  --port $PT --max-model-len ${TARGET_MAX_LEN:-24576} --gpu-memory-utilization 0.9 --enable-prefix-caching \
  > $W/logs/${NAME}_target_$SLURM_JOB_ID.log 2>&1 &
# the optimizer reads whole minibatches of trajectories: long context, and its
# thinking must be split off (--reasoning-parser) or the JSON edits do not parse
CUDA_VISIBLE_DEVICES=1 VLLM_CACHE_ROOT=/dev/shm/$USER-v1-$SLURM_JOB_ID $B/.venv/bin/vllm serve $OPT \
  --port $PO --max-model-len 131072 --gpu-memory-utilization 0.92 --enable-prefix-caching --max-num-seqs 32 --reasoning-parser qwen3 \
  > $W/logs/${NAME}_optimizer_$SLURM_JOB_ID.log 2>&1 &
for p in $PT $PO; do
  for i in $(seq 1 120); do curl -sf localhost:$p/health >/dev/null && break; sleep 10; done
  curl -sf localhost:$p/health >/dev/null || { echo "[job] server on $p failed, see $W/logs"; exit 1; }
done
echo "[job] servers up"
export TARGET_QWEN_CHAT_BASE_URL=http://localhost:$PT/v1 TARGET_QWEN_CHAT_MODEL=$TARGET
export TARGET_QWEN_CHAT_TEMPERATURE=0 TARGET_QWEN_CHAT_MAX_TOKENS=16384
export OPTIMIZER_QWEN_CHAT_BASE_URL=http://localhost:$PO/v1 OPTIMIZER_QWEN_CHAT_MODEL=$OPT
export OPTIMIZER_QWEN_CHAT_MAX_TOKENS=32768
export TARGET_QWEN_CHAT_TIMEOUT_SECONDS=900 OPTIMIZER_QWEN_CHAT_TIMEOUT_SECONDS=1800
cd $W/SkillOpt
# thinking modes MUST go through --cfg-options: the config value overrides the env var
.venv/bin/python scripts/train.py --config $CONFIG \
  --target_backend qwen_chat --optimizer_backend qwen_chat \
  --target_model $TARGET --optimizer_model $OPT \
  --cfg-options env.split_mode=split_dir env.split_dir=$SPLIT env.out_root=$W/outputs/$NAME \
    env.exec_timeout=900 model.target_qwen_chat_thinking_mode=disabled model.optimizer_qwen_chat_thinking_mode=enabled "$@"
rc=$?; echo "[job] train rc=$rc"; kill %1 %2; exit $rc
