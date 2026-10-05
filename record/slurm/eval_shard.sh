#!/bin/bash
#SBATCH --job-name=ls_eval1
#SBATCH --output=/shared/home/adil.taibassarov/latent-skills/logs/eval1_%j.out
#SBATCH -A issai
#SBATCH -p H100
#SBATCH -q issai-h100
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH -t 12:00:00
#SBATCH --exclude=g002,g006
# Re-run ONE shard of a cell. Shards die individually on transient BeeGFS read
# errors (a safetensors shard or a transformers module momentarily unreadable
# when four processes load at once), and eval.sh's bare `wait` does not notice.
#
#   SHARD=1/4 MODEL_ID=... SKILL=... SKILLPOS=user LIMIT=608 MAXNEW=4096 \
#     sbatch slurm/eval_shard.sh livemath text
set -euo pipefail
source /shared/home/adil.taibassarov/latent-skills/env.sh
DOMAIN="${1:?domain}"; COND="${2:?condition}"
VEC="${3:-}"; LAYERS="${4:-24-40}"; GAMMA="${5:-1.0}"
SHARD="${SHARD:?SHARD=i/k required}"
LIMIT="${LIMIT:-200}"; BS="${BS:-8}"; SKILL="${SKILL:-compare_claims.md}"
MAXNEW="${MAXNEW:-}"; SKILLPOS="${SKILLPOS:-system}"
mkdir -p "$TRITON_CACHE_DIR"
echo "[job] node=$(hostname -s) model=$MODEL_ID $DOMAIN/$COND shard=$SHARD pos=$SKILLPOS"
EXTRA=()
[ -n "$MAXNEW" ] && EXTRA+=(--max-new-tokens "$MAXNEW")
[ "$COND" = "embed" ] && EXTRA+=(--vectors "$LS_ROOT/$VEC" --layers "$LAYERS" --gamma "$GAMMA")
exec "$LS_PY" "$LS_ROOT/src/evaluate.py" --domain "$DOMAIN" --condition "$COND" \
     --limit "$LIMIT" --batch-size "$BS" --shard "$SHARD" \
     --skill "$LS_ROOT/skills/$SKILL" --skill-position "$SKILLPOS" "${EXTRA[@]}"
