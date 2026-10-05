#!/bin/bash
#SBATCH --job-name=ls_eval
#SBATCH --output=/shared/home/adil.taibassarov/latent-skills/logs/eval_%j.out
#SBATCH -A issai
#SBATCH -p H100
#SBATCH -q issai-h100
#SBATCH --nodes=1
#SBATCH --gpus-per-node=4
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=256G
#SBATCH -t 20:00:00
#SBATCH --exclude=g002,g006
# g006 runs jobs that consume GPU memory without requesting it via gres.
#
# Both models fit in one 80GB H100, so instead of spreading one slow
# pipeline-parallel copy over 4 GPUs we run 4 independent shards, one per GPU,
# and merge. Roughly 4x the throughput.
#
#   MODEL_ID=Qwen/Qwen3-8B LIMIT=608 sbatch slurm/eval.sh livemath baseline
#   MODEL_ID=Qwen/Qwen3-8B LIMIT=608 SKILL=compare_claims.md \
#       sbatch slurm/eval.sh livemath text
#   MODEL_ID=Qwen/Qwen3-8B LIMIT=608 \
#       sbatch slurm/eval.sh livemath embed vectors/<vec>.pt 20-28 0.2

set -euo pipefail
source /shared/home/adil.taibassarov/latent-skills/env.sh
DOMAIN="${1:?domain}"; COND="${2:?condition}"
VEC="${3:-}"; LAYERS="${4:-24-40}"; GAMMA="${5:-1.0}"
LIMIT="${LIMIT:-200}"; BS="${BS:-8}"; SKILL="${SKILL:-compare_claims.md}"
# Qwen3.6-27B is markedly more verbose than Qwen3-8B on LiveMath: at the
# 2048 default, 51.6% of its replies hit the cap mid-sentence and never
# reach the `Answer:` line, scoring 16.9% -- BELOW the 20% chance floor.
MAXNEW="${MAXNEW:-}"
SKILLPOS="${SKILLPOS:-system}"   # system | user
mkdir -p "$TRITON_CACHE_DIR"
echo "[job] node=$(hostname -s) model=$MODEL_ID $DOMAIN/$COND skill=$SKILL vec=$VEC layers=$LAYERS gamma=$GAMMA bs=$BS"

EXTRA=()
[ -n "$MAXNEW" ] && EXTRA+=(--max-new-tokens "$MAXNEW")
if [ "$COND" = "embed" ]; then
  EXTRA+=(--vectors "$LS_ROOT/$VEC" --layers "$LAYERS" --gamma "$GAMMA")
fi

# Each shard's exit status is checked individually. A bare `wait` returns only
# the LAST job's status, so a shard that dies -- e.g. on a transient BeeGFS read
# error, "does not appear to have a file named model-00001-of-00015.safetensors",
# which happens when four processes load the weights at once -- leaves the job
# exiting 0 with a quarter of the results missing. That happened on 2026-09-27
# and was caught only because report.py prints n.
PIDS=()
for i in 0 1 2 3; do
  CUDA_VISIBLE_DEVICES=$i "$LS_PY" "$LS_ROOT/src/evaluate.py" \
      --domain "$DOMAIN" --condition "$COND" --limit "$LIMIT" \
      --skill "$LS_ROOT/skills/$SKILL" --skill-position "$SKILLPOS" \
      --batch-size "$BS" --shard "$i/4" "${EXTRA[@]}" \
      > "$LS_ROOT/logs/${SLURM_JOB_ID}_shard$i.log" 2>&1 &
  PIDS+=($!)
done
FAILED=()
for i in 0 1 2 3; do
  if ! wait "${PIDS[$i]}"; then FAILED+=("$i"); fi
done
if [ "${#FAILED[@]}" -gt 0 ]; then
  echo "[job] SHARDS FAILED: ${FAILED[*]}  -- this cell is INCOMPLETE"
  for i in "${FAILED[@]}"; do
    echo "--- shard $i tail"; tail -n 8 "$LS_ROOT/logs/${SLURM_JOB_ID}_shard$i.log"
    echo "--- re-run with: SHARD=$i/4 MODEL_ID=$MODEL_ID LIMIT=$LIMIT BS=$BS \\"
    echo "      SKILL=$SKILL SKILLPOS=$SKILLPOS ${MAXNEW:+MAXNEW=$MAXNEW }\\"
    echo "      sbatch slurm/eval_shard.sh $DOMAIN $COND $VEC $LAYERS $GAMMA"
  done
  exit 1
fi
echo "[job] all 4 shards OK"
tail -n 20 "$LS_ROOT/logs/${SLURM_JOB_ID}_shard0.log"
