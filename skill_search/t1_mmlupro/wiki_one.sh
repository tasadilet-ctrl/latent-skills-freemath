#!/bin/bash
# One WikiSkill evolution (wikiskill.py) on the MMLU-Pro T1 split, servers as train_one.sh: answering model on GPU 0
# (thinking off, T 1.0), maintainer + proposer Qwen3.6-27B on GPU 1 (thinking on, T 1.0).
#   wiki_one.sh <size> <R>        -> ~/skillopt_work/outputs/wiki_t1_<size>_r<R>/   (env SPLIT, ITERS override)
set -uo pipefail
S=$1; R=$2
H=$(cd "$(dirname "$0")" && pwd); W=$HOME/skillopt_work; VENV=$W/vllm_env; B=${SPLIT:-mmlupro_math_tq_sb}
declare -A HF=([4b]=Qwen/Qwen3-4B [8b]=Qwen/Qwen3-8B [14b]=Qwen/Qwen3-14B [27b]=Qwen/Qwen3.6-27B)
declare -A TOK=([4b]=2048 [8b]=2048 [14b]=2048 [27b]=4096)
TARGET=${HF[$S]}; OPT=Qwen/Qwen3.6-27B; NAME=wiki_t1_${S}_r$R; OUT=$W/outputs/$NAME
export HF_HUB_OFFLINE=1 PATH=$VENV/bin:$PATH
mkdir -p $W/logs
free_port() { while :; do p=$((20000 + RANDOM % 20000)); ss -ltn | awk '{print $4}' | grep -q ":$p\$" || { echo $p; return; }; done; }
PT=$(free_port); PO=$(free_port); while [ "$PO" = "$PT" ]; do PO=$(free_port); done
echo "[wiki] $NAME target=$TARGET seed=$R ports=$PT/$PO $(date '+%F %T')"
CUDA_VISIBLE_DEVICES=1 VLLM_CACHE_ROOT=/dev/shm/$USER-wk-opt vllm serve $OPT --port $PO \
  --max-model-len 131072 --gpu-memory-utilization 0.92 --enable-prefix-caching --attention-backend FLASHINFER \
  --max-num-seqs 32 --reasoning-parser qwen3 > $W/logs/${NAME}_optimizer.log 2>&1 &
SO=$!
CUDA_VISIBLE_DEVICES=0 VLLM_CACHE_ROOT=/dev/shm/$USER-wk-tgt vllm serve $TARGET --port $PT \
  --max-model-len 16384 --gpu-memory-utilization 0.90 --enable-prefix-caching --attention-backend FLASHINFER \
  --max-num-seqs 256 > $W/logs/${NAME}_target.log 2>&1 &
ST=$!
trap 'kill $SO $ST 2>/dev/null; wait $SO $ST 2>/dev/null' EXIT
for p in $PO $PT; do
  for i in $(seq 1 120); do curl -sf localhost:$p/health >/dev/null && break; sleep 10; done
  curl -sf localhost:$p/health >/dev/null || { echo "[wiki] server on $p failed, see $W/logs/${NAME}_*.log"; exit 1; }
done
echo "[wiki] servers up $(date '+%T')"
$VENV/bin/python $H/wikiskill.py --split-dir $W/mq_split/$B --out $OUT --seed $R --iters ${ITERS:-8} \
  --target-url http://localhost:$PT/v1 --target-model $TARGET --opt-url http://localhost:$PO/v1 --opt-model $OPT \
  --max-tokens ${TOK[$S]} > $W/logs/${NAME}_wiki.log 2>&1
rc=$?; echo "[wiki] $NAME rc=$rc $(date '+%F %T')"; exit $rc
