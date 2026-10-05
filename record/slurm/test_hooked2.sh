#!/bin/bash
#SBATCH --job-name=ls_hook2
#SBATCH --output=/shared/home/adil.taibassarov/latent-skills/logs/hook2_%j.out
#SBATCH -A issai
#SBATCH -p H100
#SBATCH -q issai-h100
#SBATCH --nodes=1
#SBATCH --gpus-per-node=2
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH -t 01:00:00
#SBATCH --exclude=g002,g006
# Does steering take effect THROUGH THE SERVER? The earlier test used a trivial
# "list the files" prompt where the model is near-certain, so steered and
# unsteered produced byte-identical output -- which cannot distinguish "hooks
# work" from "hooks silently do nothing". This sends REAL benchmark prompts and
# compares the two outputs directly.
set -uo pipefail
source /shared/home/adil.taibassarov/latent-skills/env.sh
PORT=8078
VEC="${VEC:-vectors/v_qwen3-14b_compare_claims_v3_livemath_n50_placebo.pt}"
LAYERS="${LAYERS:-37}"; GAMMA="${GAMMA:-0.3}"

start() {
  MODEL_ID="$MODEL_ID" "$LS_PY" "$LS_ROOT/src/serve_hooked.py" --port $PORT \
     --served-name test $1 > "$LS_ROOT/logs/hook2_${SLURM_JOB_ID}_srv$2.log" 2>&1 &
  echo $!
}
ready() { for i in $(seq 1 120); do
    curl -sf -m 5 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && return 0
    kill -0 "$1" 2>/dev/null || return 1; sleep 10; done; return 1; }

echo "phase 1: UNSTEERED"
P=$(start "" a); ready "$P" || { tail -20 "$LS_ROOT/logs/hook2_${SLURM_JOB_ID}_srva.log"; exit 1; }
"$LS_PY" "$LS_ROOT/src/probe_server.py" --port $PORT --out "$LS_ROOT/logs/hook2_${SLURM_JOB_ID}_plain.json"
kill "$P" 2>/dev/null; sleep 25

echo "phase 2: STEERED L$LAYERS g$GAMMA"
P=$(start "--vectors $LS_ROOT/$VEC --layers $LAYERS --gamma $GAMMA" b); ready "$P" || exit 1
curl -s -m 10 "http://127.0.0.1:$PORT/health"; echo
"$LS_PY" "$LS_ROOT/src/probe_server.py" --port $PORT --out "$LS_ROOT/logs/hook2_${SLURM_JOB_ID}_steer.json"
kill "$P" 2>/dev/null

echo; echo "phase 3: COMPARE"
"$LS_PY" "$LS_ROOT/src/probe_server.py" --compare \
   "$LS_ROOT/logs/hook2_${SLURM_JOB_ID}_plain.json" \
   "$LS_ROOT/logs/hook2_${SLURM_JOB_ID}_steer.json"
