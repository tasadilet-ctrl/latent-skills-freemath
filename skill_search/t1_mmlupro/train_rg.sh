#!/bin/bash
# One SkillOpt training on a Reasoning Gym task (positive control), same stack as train_one.sh: target on GPU 0
# (thinking off, T 1.0), optimizer Qwen3.6-27B on GPU 1 (thinking on, T 1.0), 4 epochs, batch 60 = whole train
# split, validation 40 questions x RGYM_VAL_REPEATS (default 4). Starting skill: the one-liner (rgym_env/initial.md).
#   train_rg.sh <size> <task>        e.g. train_rg.sh 8b products       Output: outputs/rg_<task>_<size>_r1
# Optional env: RUN_NAME, RG_SPLIT (split root, default ~/skillopt_work/rg_split), BATCH (60), EPOCHS (4).
set -uo pipefail
S=$1; TASK=$2; R=1
W=$HOME/skillopt_work; VENV=$W/vllm_env
declare -A HF=([4b]=Qwen/Qwen3-4B [8b]=Qwen/Qwen3-8B [14b]=Qwen/Qwen3-14B [27b]=Qwen/Qwen3.6-27B)
TARGET=${HF[$S]}; OPT=Qwen/Qwen3.6-27B
NAME=${RUN_NAME:-rg_${TASK}_${S}_r$R}; OUT=$W/outputs/$NAME
export HF_HUB_OFFLINE=1 PATH=$VENV/bin:$PATH RGYM_VAL_REPEATS=${RGYM_VAL_REPEATS:-4}
mkdir -p $W/logs
free_port() { while :; do p=$((20000 + RANDOM % 20000)); ss -ltn | awk '{print $4}' | grep -q ":$p\$" || { echo $p; return; }; done; }
PT=$(free_port); PO=$(free_port); while [ "$PO" = "$PT" ]; do PO=$(free_port); done
echo "[train] $NAME target=$TARGET ports=$PT/$PO $(date '+%F %T')"
CUDA_VISIBLE_DEVICES=1 VLLM_CACHE_ROOT=/dev/shm/$USER-t1-opt vllm serve $OPT --port $PO \
  --max-model-len 131072 --gpu-memory-utilization 0.92 --enable-prefix-caching --attention-backend FLASHINFER \
  --max-num-seqs 32 --reasoning-parser qwen3 > $W/logs/${NAME}_optimizer.log 2>&1 &
SO=$!
CUDA_VISIBLE_DEVICES=0 VLLM_CACHE_ROOT=/dev/shm/$USER-t1-tgt vllm serve $TARGET --port $PT \
  --max-model-len 16384 --gpu-memory-utilization 0.90 --enable-prefix-caching --attention-backend FLASHINFER \
  --max-num-seqs 256 > $W/logs/${NAME}_target.log 2>&1 &
ST=$!
trap 'kill $SO $ST 2>/dev/null; wait $SO $ST 2>/dev/null' EXIT
for p in $PO $PT; do
  for i in $(seq 1 120); do curl -sf localhost:$p/health >/dev/null && break; sleep 10; done
  curl -sf localhost:$p/health >/dev/null || { echo "[train] server on $p failed"; exit 1; }
done
export TARGET_QWEN_CHAT_BASE_URL=http://localhost:$PT/v1 TARGET_QWEN_CHAT_MODEL=$TARGET
export TARGET_QWEN_CHAT_TEMPERATURE=1.0 TARGET_QWEN_CHAT_MAX_TOKENS=16384
export OPTIMIZER_QWEN_CHAT_BASE_URL=http://localhost:$PO/v1 OPTIMIZER_QWEN_CHAT_MODEL=$OPT
export OPTIMIZER_QWEN_CHAT_TEMPERATURE=1.0 OPTIMIZER_QWEN_CHAT_MAX_TOKENS=32768
export TARGET_QWEN_CHAT_TIMEOUT_SECONDS=900 OPTIMIZER_QWEN_CHAT_TIMEOUT_SECONDS=1800
cd $W/SkillOpt
.venv/bin/python scripts/train.py --config configs/rgym/default.yaml \
  --target_backend qwen_chat --optimizer_backend qwen_chat --target_model $TARGET --optimizer_model $OPT \
  --cfg-options env.split_mode=split_dir env.split_dir=${RG_SPLIT:-$W/rg_split}/$TASK env.out_root=$OUT env.exec_timeout=900 \
    env.max_completion_tokens=2048 evaluation.eval_test=false train.batch_size=${BATCH:-60} train.num_epochs=${EPOCHS:-4} train.seed=$R \
    model.target_qwen_chat_temperature=1.0 model.optimizer_qwen_chat_temperature=1.0 \
    model.target_qwen_chat_thinking_mode=disabled model.optimizer_qwen_chat_thinking_mode=enabled \
  > $W/logs/${NAME}_train.log 2>&1
rc=$?; echo "[train] $NAME rc=$rc $(date '+%F %T')"; exit $rc
