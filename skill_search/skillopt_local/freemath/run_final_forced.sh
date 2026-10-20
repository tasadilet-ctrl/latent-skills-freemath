#!/usr/bin/env bash
# Re-score the final comparison with the forcing pass on (env.force_answer=true),
# into final_eval_forced/, for every benchmark that has a best_skill.md. Training
# is not re-run. Start it after run_freemath_local.sh has finished (it needs the GPUs).
#   ./run_final_forced.sh [target model] [benchmarks...]
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
W=${SKILLOPT_WORK:-$HOME/skillopt_work}
VENV=${VLLM_VENV:-$W/vllm_env}
KIT_SKILLS=${KIT_SKILLS:-$HOME/for Adilet/skills}
TARGET=${1:-Qwen/Qwen3-8B}; shift || true
BENCHES=${*:-beyondaime hardmath2 realmath}
TAG=$(basename "$TARGET" | tr A-Z a-z)
export HF_HUB_OFFLINE=1 PATH=$VENV/bin:$PATH
"$HERE/install_env.sh" "$W/SkillOpt"
PT=18100
CUDA_VISIBLE_DEVICES=${GPU:-0} VLLM_CACHE_ROOT=/dev/shm/$USER-fm-tgt vllm serve $TARGET --port $PT \
  --max-model-len 24576 --gpu-memory-utilization 0.90 --enable-prefix-caching > "$W/logs/fm_forced_target.log" 2>&1 &
ST=$!; trap 'kill $ST 2>/dev/null' EXIT
for i in $(seq 1 120); do curl -sf localhost:$PT/health >/dev/null && break; sleep 10; done
curl -sf localhost:$PT/health >/dev/null || { echo "[forced] target server failed"; exit 1; }
export TARGET_QWEN_CHAT_BASE_URL=http://localhost:$PT/v1 TARGET_QWEN_CHAT_MODEL=$TARGET
export TARGET_QWEN_CHAT_TEMPERATURE=0 TARGET_QWEN_CHAT_MAX_TOKENS=16384 TARGET_QWEN_CHAT_TIMEOUT_SECONDS=900
# eval_only builds an optimizer client it never calls; point it at the same server
export OPTIMIZER_QWEN_CHAT_BASE_URL=http://localhost:$PT/v1 OPTIMIZER_QWEN_CHAT_MODEL=$TARGET
cd "$W/SkillOpt"; : > "$W/empty_skill.md"
for b in $BENCHES; do
  OUT=$W/outputs/fm_${b}_${TAG}; SPLIT=$W/fm_split/$b
  [ -f "$OUT/best_skill.md" ] || { echo "[forced] skip $b (no best_skill.md)"; continue; }
  for cond in none placebo strength_audit skillopt; do
    case $cond in
      none) SK=$W/empty_skill.md ;; placebo) SK="$KIT_SKILLS/placebo_matched.md" ;;
      strength_audit) SK="$KIT_SKILLS/strength_audit.md" ;; skillopt) SK=$OUT/best_skill.md ;;
    esac
    [ -f "$OUT/final_eval_forced/$cond/eval_summary.json" ] && continue
    .venv/bin/python scripts/eval_only.py --config configs/freemath/default.yaml --skill "$SK" --split test \
      --target_backend qwen_chat --optimizer_backend qwen_chat --target_model $TARGET --optimizer_model $TARGET \
      --cfg-options env.split_mode=split_dir env.split_dir=$SPLIT env.out_root=$OUT/final_eval_forced/$cond \
      env.force_answer=true model.target_qwen_chat_thinking_mode=disabled \
      > "$W/logs/fm_forced_${b}_${TAG}_${cond}.log" 2>&1
    echo "[forced] eval $b $cond rc=$?"
  done
done
echo "[forced] ALL_DONE"
