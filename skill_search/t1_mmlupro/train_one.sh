#!/bin/bash
# One SkillOpt training at temperature 1.0 on MMLU-Pro math (GUIDE_T1_5RUNS.md section 4), workstation version
# of run_skillopt.sbatch: target on GPU 0, optimizer Qwen3.6-27B on GPU 1, both FlashInfer.
#
#   train_one.sh <size> <R> [extra --cfg-options ...]      size in 4b 8b 14b 27b, R = run (= train.seed)
#   env: RUN_NAME (output name), SPLIT (dir under mq_split, default mmlupro_math_tq_sb), BATCH (default 40)
#
# Env mcqkit = mcqmath with the kit runner's prompt, forcing and parser (identical to evaluate_mcq_t1.py),
# options not shuffled. Split = the paper's pre-registered one (mq_split: train 40 / val 100 / test 365);
# batch 40 = the whole train split, 4 epochs = 4 steps. Output: ~/skillopt_work/outputs/$RUN_NAME/.
set -uo pipefail
S=$1; R=$2; shift 2
W=$HOME/skillopt_work; VENV=$W/vllm_env; B=${SPLIT:-mmlupro_math_tq_sb}; BATCH=${BATCH:-40}
declare -A HF=([4b]=Qwen/Qwen3-4B [8b]=Qwen/Qwen3-8B [14b]=Qwen/Qwen3-14B [27b]=Qwen/Qwen3.6-27B)
declare -A TOK=([4b]=2048 [8b]=2048 [14b]=2048 [27b]=4096)
TARGET=${HF[$S]}; OPT=Qwen/Qwen3.6-27B
NAME=${RUN_NAME:-mq_t1_${S}_r$R}; OUT=$W/outputs/$NAME
export HF_HUB_OFFLINE=1 PATH=$VENV/bin:$PATH
mkdir -p $W/logs
free_port() { while :; do p=$((20000 + RANDOM % 20000)); ss -ltn | awk '{print $4}' | grep -q ":$p\$" || { echo $p; return; }; done; }
PT=$(free_port); PO=$(free_port); while [ "$PO" = "$PT" ]; do PO=$(free_port); done
echo "[train] $NAME target=$TARGET seed=$R ports=$PT/$PO $(date '+%F %T')"
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
  curl -sf localhost:$p/health >/dev/null || { echo "[train] server on $p failed, see $W/logs/${NAME}_*.log"; exit 1; }
done
kill -0 $SO 2>/dev/null && kill -0 $ST 2>/dev/null || { echo "[train] a server died"; exit 1; }
echo "[train] servers up $(date '+%T')"
export TARGET_QWEN_CHAT_BASE_URL=http://localhost:$PT/v1 TARGET_QWEN_CHAT_MODEL=$TARGET
export TARGET_QWEN_CHAT_TEMPERATURE=1.0 TARGET_QWEN_CHAT_MAX_TOKENS=16384
export OPTIMIZER_QWEN_CHAT_BASE_URL=http://localhost:$PO/v1 OPTIMIZER_QWEN_CHAT_MODEL=$OPT
export OPTIMIZER_QWEN_CHAT_TEMPERATURE=1.0 OPTIMIZER_QWEN_CHAT_MAX_TOKENS=32768
export TARGET_QWEN_CHAT_TIMEOUT_SECONDS=900 OPTIMIZER_QWEN_CHAT_TIMEOUT_SECONDS=1800
cd $W/SkillOpt
# temperatures and thinking modes MUST go through --cfg-options: the config value overrides the env var
.venv/bin/python scripts/train.py --config configs/mcqkit/default.yaml \
  --target_backend qwen_chat --optimizer_backend qwen_chat --target_model $TARGET --optimizer_model $OPT \
  --cfg-options env.split_mode=split_dir env.split_dir=$W/mq_split/$B env.out_root=$OUT env.exec_timeout=900 \
    env.max_completion_tokens=${TOK[$S]} evaluation.eval_test=false train.batch_size=$BATCH train.seed=$R \
    model.target_qwen_chat_temperature=1.0 model.optimizer_qwen_chat_temperature=1.0 \
    model.target_qwen_chat_thinking_mode=disabled model.optimizer_qwen_chat_thinking_mode=enabled "$@" \
  > $W/logs/${NAME}_train.log 2>&1
rc=$?; echo "[train] $NAME rc=$rc $(date '+%F %T')"; exit $rc
