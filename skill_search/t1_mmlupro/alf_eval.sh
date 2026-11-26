#!/bin/bash
# Test one skill file on ALFWorld's 134 test games (valid_unseen, SkillOpt's alfworld_path_split) with SkillOpt's
# own runner (scripts/eval_only.py): Qwen3 answers on one GPU, thinking ON (THINK=disabled turns it off), T 1.0,
# up to 50 actions per game. Thinking is on because with it off Qwen3-8B reasoned in only 4% of steps (4B: 100%)
# and solved 7.5% of games: ALFWorld's prompt asks for <think> reasoning before each <action>.
# An empty skill file = no skill (SkillOpt then adds no skill section to the prompt).
#   alf_eval.sh <size> <skill file> <out name> [gpu]   -> ~/skillopt_work/outputs/<out name>/eval_summary.json
set -uo pipefail
S=$1; SK=$(readlink -f $2); NAME=$3; G=${4:-0}
W=$HOME/skillopt_work; VENV=$W/vllm_env; OUT=$W/outputs/$NAME
declare -A HF=([4b]=Qwen/Qwen3-4B [8b]=Qwen/Qwen3-8B [14b]=Qwen/Qwen3-14B [27b]=Qwen/Qwen3.6-27B)
TARGET=${HF[$S]}
export HF_HUB_OFFLINE=1 PATH=$VENV/bin:$PATH ALFWORLD_DATA=$HOME/.cache/alfworld
[ -s $OUT/eval_summary.json ] && { echo "[alf eval] $NAME exists"; exit 0; }
mkdir -p $W/logs
free_port() { while :; do p=$((20000 + RANDOM % 20000)); ss -ltn | awk '{print $4}' | grep -q ":$p\$" || { echo $p; return; }; done; }
PT=$(free_port)
CUDA_VISIBLE_DEVICES=$G VLLM_CACHE_ROOT=/dev/shm/$USER-alf-$G vllm serve $TARGET --port $PT \
  --max-model-len 32768 --gpu-memory-utilization 0.90 --enable-prefix-caching --attention-backend FLASHINFER \
  --max-num-seqs 256 > $W/logs/${NAME}_target.log 2>&1 &
ST=$!
trap 'kill $ST 2>/dev/null; wait $ST 2>/dev/null' EXIT
for i in $(seq 1 120); do curl -sf localhost:$PT/health >/dev/null && break; sleep 10; done
curl -sf localhost:$PT/health >/dev/null || { echo "[alf eval] server failed"; exit 1; }
export TARGET_QWEN_CHAT_BASE_URL=http://localhost:$PT/v1 TARGET_QWEN_CHAT_MODEL=$TARGET
export TARGET_QWEN_CHAT_TEMPERATURE=1.0 TARGET_QWEN_CHAT_MAX_TOKENS=16384 TARGET_QWEN_CHAT_TIMEOUT_SECONDS=900
cd $W/SkillOpt
echo "[alf eval] $NAME skill=$SK $(date '+%F %T')"
.venv/bin/python scripts/eval_only.py --config configs/alfworld/default.yaml --skill $SK --split valid_unseen \
  --target_backend qwen_chat --optimizer_backend qwen_chat --target_model $TARGET --optimizer_model $TARGET \
  --out_root $OUT --cfg-options model.target_qwen_chat_temperature=1.0 model.target_qwen_chat_thinking_mode=${THINK:-enabled} \
    env.workers=32 env.max_api_workers=64 \
  > $W/logs/${NAME}_eval.log 2>&1
rc=$?; echo "[alf eval] $NAME rc=$rc $(date '+%F %T')"; exit $rc
