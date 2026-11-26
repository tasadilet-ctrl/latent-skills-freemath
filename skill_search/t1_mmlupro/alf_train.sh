#!/bin/bash
# One SkillOpt training on ALFWorld (2026-11-25), servers and settings as train_one.sh: target Qwen3 on GPU 0 (thinking
# ON as alf_eval.sh, T 1.0), optimizer Qwen3.6-27B on GPU 1 (thinking on, T 1.0). SkillOpt's own ALFWorld config: split
# alfworld_path_split (train 39 / val 18 / test 134), starting skill skillopt/envs/alfworld/skills/initial.md, batch 40
# (= all 39 training games, 1 step per epoch), 4 epochs, edit budget 4, up to 50 actions per game. Test is run
# separately (alf_eval.sh) so no-skill and skill cells use the same runner.
#   alf_train.sh <size> <R> [extra --cfg-options]     -> ~/skillopt_work/outputs/alf_<size>_r<R>/
set -uo pipefail
S=$1; R=$2; shift 2
W=$HOME/skillopt_work; VENV=$W/vllm_env
declare -A HF=([4b]=Qwen/Qwen3-4B [8b]=Qwen/Qwen3-8B [14b]=Qwen/Qwen3-14B [27b]=Qwen/Qwen3.6-27B)
TARGET=${HF[$S]}; OPT=Qwen/Qwen3.6-27B
NAME=${RUN_NAME:-alf_${S}_r$R}; OUT=$W/outputs/$NAME
export HF_HUB_OFFLINE=1 PATH=$VENV/bin:$PATH ALFWORLD_DATA=$HOME/.cache/alfworld
mkdir -p $W/logs
free_port() { while :; do p=$((20000 + RANDOM % 20000)); ss -ltn | awk '{print $4}' | grep -q ":$p\$" || { echo $p; return; }; done; }
PT=$(free_port); PO=$(free_port); while [ "$PO" = "$PT" ]; do PO=$(free_port); done
echo "[alf train] $NAME target=$TARGET seed=$R ports=$PT/$PO $(date '+%F %T')"
CUDA_VISIBLE_DEVICES=1 VLLM_CACHE_ROOT=/dev/shm/$USER-alf-opt vllm serve $OPT --port $PO \
  --max-model-len 131072 --gpu-memory-utilization 0.92 --enable-prefix-caching --attention-backend FLASHINFER \
  --max-num-seqs 32 --reasoning-parser qwen3 > $W/logs/${NAME}_optimizer.log 2>&1 &
SO=$!
CUDA_VISIBLE_DEVICES=0 VLLM_CACHE_ROOT=/dev/shm/$USER-alf-tgt vllm serve $TARGET --port $PT \
  --max-model-len 32768 --gpu-memory-utilization 0.90 --enable-prefix-caching --attention-backend FLASHINFER \
  --max-num-seqs 256 > $W/logs/${NAME}_target.log 2>&1 &
ST=$!
trap 'kill $SO $ST 2>/dev/null; wait $SO $ST 2>/dev/null' EXIT
for p in $PO $PT; do
  for i in $(seq 1 120); do curl -sf localhost:$p/health >/dev/null && break; sleep 10; done
  curl -sf localhost:$p/health >/dev/null || { echo "[alf train] server on $p failed"; exit 1; }
done
export TARGET_QWEN_CHAT_BASE_URL=http://localhost:$PT/v1 TARGET_QWEN_CHAT_MODEL=$TARGET
export TARGET_QWEN_CHAT_TEMPERATURE=1.0 TARGET_QWEN_CHAT_MAX_TOKENS=16384
export OPTIMIZER_QWEN_CHAT_BASE_URL=http://localhost:$PO/v1 OPTIMIZER_QWEN_CHAT_MODEL=$OPT
export OPTIMIZER_QWEN_CHAT_TEMPERATURE=1.0 OPTIMIZER_QWEN_CHAT_MAX_TOKENS=32768
export TARGET_QWEN_CHAT_TIMEOUT_SECONDS=900 OPTIMIZER_QWEN_CHAT_TIMEOUT_SECONDS=1800
cd $W/SkillOpt
.venv/bin/python scripts/train.py --config configs/alfworld/default.yaml \
  --target_backend qwen_chat --optimizer_backend qwen_chat --target_model $TARGET --optimizer_model $OPT \
  --cfg-options env.out_root=$OUT evaluation.eval_test=false train.seed=$R env.workers=32 env.max_api_workers=64 \
    model.target_qwen_chat_temperature=1.0 model.optimizer_qwen_chat_temperature=1.0 \
    model.target_qwen_chat_thinking_mode=${THINK:-enabled} model.optimizer_qwen_chat_thinking_mode=enabled "$@" \
  > $W/logs/${NAME}_train.log 2>&1
rc=$?; echo "[alf train] $NAME rc=$rc $(date '+%F %T')"; exit $rc
