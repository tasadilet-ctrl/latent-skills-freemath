#!/usr/bin/env bash
# SkillOpt on BeyondAIME, HARDMath2 and RealMath, then the final test-split comparison.
# The workstation (no SLURM) version of ../run_skillopt.sbatch: same two vLLM servers,
# same train.py flags. Servers start once and serve every benchmark.
#
#   ./run_freemath_local.sh [target model] [benchmarks...]
#     default: Qwen/Qwen3-8B  beyondaime hardmath2 realmath   (arxivmath also available)
#
# GPUs: target on GPU0 and optimizer on GPU1 when both are free (as the sbatch
# job does). If GPU1 holds someone else's memory (> 2 GB, the kit's run.sh
# rule), both servers share GPU0: the 27B's hybrid attention keeps its KV cache
# small enough. Set GPUS=0,1 or GPUS=0 to force a layout.
#
# Per benchmark, in $W/outputs/fm_<bench>_<model>/:
#   best_skill.md, summary.json, ...          the SkillOpt run (README section 6)
#   final_eval/<condition>/                   test split: none / placebo / strength_audit / skillopt
#
# SMOKE=1: README's plumbing check (1 epoch, batch 8, 16 items per split) into
# fm_<bench>_<model>_smoke/. Run it before the real thing.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
W=${SKILLOPT_WORK:-$HOME/skillopt_work}
VENV=${VLLM_VENV:-$W/vllm_env}
KIT_SKILLS=${KIT_SKILLS:-$HOME/for Adilet/skills}
TARGET=${1:-Qwen/Qwen3-8B}; shift || true
BENCHES=${*:-beyondaime hardmath2 realmath}
OPT=${OPTIMIZER:-Qwen/Qwen3.6-27B}
TAG=$(basename "$TARGET" | tr A-Z a-z)
EXTRA=(); SFX=""
[ "${SMOKE:-0}" = 1 ] && EXTRA=(train.num_epochs=1 train.batch_size=8 env.limit=16) SFX=_smoke
export HF_HUB_OFFLINE=1 PATH=$VENV/bin:$PATH
mkdir -p "$W/logs"

used1=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i 1 2>/dev/null || echo 99999)
GPUS=${GPUS:-$([ "${used1:-99999}" -le 2000 ] && echo 0,1 || echo 0)}
if [ "$GPUS" = 0,1 ]; then GT=0 GO=1 UT=0.90 UO=0.92 NSEQ=32
else                     GT=0 GO=0 UT=0.28 UO=0.68 NSEQ=8; fi
PT=18100 PO=18101
echo "[fm] target=$TARGET optimizer=$OPT gpus=$GPUS benches=$BENCHES"

# optimizer first: the second server on a shared card sizes itself from what is left
CUDA_VISIBLE_DEVICES=$GO VLLM_CACHE_ROOT=/dev/shm/$USER-fm-opt vllm serve $OPT --port $PO \
  --max-model-len 131072 --gpu-memory-utilization $UO --enable-prefix-caching --max-num-seqs $NSEQ \
  --reasoning-parser qwen3 > "$W/logs/fm_optimizer.log" 2>&1 &
SO=$!
for i in $(seq 1 120); do curl -sf localhost:$PO/health >/dev/null && break; sleep 10; done
CUDA_VISIBLE_DEVICES=$GT VLLM_CACHE_ROOT=/dev/shm/$USER-fm-tgt vllm serve $TARGET --port $PT \
  --max-model-len 24576 --gpu-memory-utilization $UT --enable-prefix-caching \
  > "$W/logs/fm_target.log" 2>&1 &
ST=$!
trap 'kill $SO $ST 2>/dev/null' EXIT
for p in $PO $PT; do
  for i in $(seq 1 120); do curl -sf localhost:$p/health >/dev/null && break; sleep 10; done
  curl -sf localhost:$p/health >/dev/null || { echo "[fm] server on $p failed, see $W/logs/fm_*.log"; exit 1; }
done
echo "[fm] servers up"

export TARGET_QWEN_CHAT_BASE_URL=http://localhost:$PT/v1 TARGET_QWEN_CHAT_MODEL=$TARGET
export TARGET_QWEN_CHAT_TEMPERATURE=0 TARGET_QWEN_CHAT_MAX_TOKENS=16384
export OPTIMIZER_QWEN_CHAT_BASE_URL=http://localhost:$PO/v1 OPTIMIZER_QWEN_CHAT_MODEL=$OPT
export OPTIMIZER_QWEN_CHAT_MAX_TOKENS=32768
export TARGET_QWEN_CHAT_TIMEOUT_SECONDS=900 OPTIMIZER_QWEN_CHAT_TIMEOUT_SECONDS=1800
COMMON=(--target_backend qwen_chat --optimizer_backend qwen_chat --target_model $TARGET --optimizer_model $OPT)
THINK=(model.target_qwen_chat_thinking_mode=disabled model.optimizer_qwen_chat_thinking_mode=enabled)
cd "$W/SkillOpt"
: > "$W/empty_skill.md"

for b in $BENCHES; do
  OUT=$W/outputs/fm_${b}_${TAG}${SFX}; SPLIT=$W/fm_split/$b
  if [ ! -f "$OUT/best_skill.md" ]; then
    echo "[fm] train $b"
    .venv/bin/python scripts/train.py --config configs/freemath/default.yaml "${COMMON[@]}" \
      --cfg-options env.split_mode=split_dir env.split_dir=$SPLIT env.out_root=$OUT env.exec_timeout=900 "${THINK[@]}" "${EXTRA[@]}" \
      > "$W/logs/fm_train_${b}_${TAG}${SFX}.log" 2>&1
    echo "[fm] train $b rc=$?"
  fi
  [ -f "$OUT/best_skill.md" ] || { echo "[fm] TRAIN_FAILED $b"; continue; }
  # The final comparison: every condition on the identical test items, same server, same prompt.
  for cond in none placebo strength_audit skillopt; do
    case $cond in
      none) SK=$W/empty_skill.md ;; placebo) SK="$KIT_SKILLS/placebo_matched.md" ;;
      strength_audit) SK="$KIT_SKILLS/strength_audit.md" ;; skillopt) SK=$OUT/best_skill.md ;;
    esac
    [ -f "$OUT/final_eval/$cond/eval_summary.json" ] && continue
    .venv/bin/python scripts/eval_only.py --config configs/freemath/default.yaml --skill "$SK" --split test \
      "${COMMON[@]}" --cfg-options env.split_mode=split_dir env.split_dir=$SPLIT \
      env.out_root=$OUT/final_eval/$cond "${THINK[@]}" "${EXTRA[@]}" > "$W/logs/fm_eval_${b}_${TAG}${SFX}_${cond}.log" 2>&1
    echo "[fm] eval $b $cond rc=$?"
  done
  echo "[fm] BENCH_DONE $b"
done
echo "[fm] ALL_DONE"
