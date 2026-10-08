#!/usr/bin/env bash
# env.sh -- paths and knobs. Every script in this kit sources it; you should
# not normally need to run it yourself.
#
# Everything resolves relative to this file, so the kit works wherever you put
# it and whatever you rename it to. Nothing here points outside the kit except
# the model cache, which is deliberately shared (the weights are ~16-60 GB per
# model and should not be duplicated per checkout).

KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export KIT

# ---------------------------------------------------------------- layout ----
export LS_ROOT="$KIT"
export RESULTS="$KIT/results"
export VECTORS="$KIT/vectors"
export LOGS="$KIT/logs"
export DATA="$KIT/data"
mkdir -p "$RESULTS" "$VECTORS" "$LOGS"

export PYTHONPATH="$KIT:$KIT/pylibs:${PYTHONPATH:-}"

# --------------------------------------------------------------- pythons ----
# Three environments, because their dependencies genuinely conflict:
#   EVAL   torch + transformers. Runs every direct benchmark and the hooks.
#   AGENT  strands-agents (needs py>=3.10, pulls its own openai tree). The
#          agent harness only. Keeping it apart stops it reinstalling torch.
#   PLOT   matplotlib only, for the PNG table.
export PY_EVAL="${PY_EVAL:-$KIT/.venv/bin/python}"
export PY_AGENT="${PY_AGENT:-$KIT/.agentvenv/bin/python}"
export PY_PLOT="${PY_PLOT:-$KIT/.plotvenv/bin/python}"

# ---------------------------------------------------------------- models ----
# Hugging Face ids. MODEL_TAG is what appears in result filenames and tables --
# keep it stable or cells from the same model will not merge.
export MODEL_ID="${MODEL_ID:-Qwen/Qwen3-8B}"
case "$MODEL_ID" in
  *Qwen3-8B*)    DEFAULT_TAG="qwen3-8b"    ;;
  *Qwen3-14B*)   DEFAULT_TAG="qwen3-14b"   ;;
  *Qwen3.6-27B*) DEFAULT_TAG="qwen3.6-27b" ;;
  *)             DEFAULT_TAG="$(basename "$MODEL_ID" | tr 'A-Z' 'a-z')" ;;
esac
export MODEL_TAG="${MODEL_TAG:-$DEFAULT_TAG}"

# Shared weight cache. Point HF_HOME elsewhere to use your own.
export HF_HOME="${HF_HOME:-$KIT/.hf_cache}"
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-0}"
export TOKENIZERS_PARALLELISM=false

# --------------------------------------------------------------- compute ----
# RUNNER decides how a cell is executed:
#   sbatch  submit to SLURM           (a shared cluster)
#   local   run here, now, foreground (a workstation with GPUs)
# Auto-detected: SLURM if sbatch exists, otherwise local.
if [ -z "${RUNNER:-}" ]; then
  if command -v sbatch >/dev/null 2>&1; then RUNNER=sbatch; else RUNNER=local; fi
fi
export RUNNER

# Which GPUs `local` may use. GPU=0 / GPU=1 / GPU=0,1 ...
export GPU="${GPU:-0}"

# SLURM placement (ignored when RUNNER=local).
export SLURM_ACCOUNT="${SLURM_ACCOUNT:-issai}"
export SLURM_PARTITION="${SLURM_PARTITION:-H100}"
export SLURM_QOS="${SLURM_QOS:-issai-h100}"
export SLURM_GPUS="${SLURM_GPUS:-4}"
# g002's munge auth died 2026-08-14 and SLURM still reports it IDLE; g006 runs
# jobs that hold GPU memory without requesting it through gres. Never schedule
# on either.
export SLURM_EXCLUDE="${SLURM_EXCLUDE:-g002,g006}"
export TRITON_CACHE_DIR="${TRITON_CACHE_DIR:-/dev/shm/$USER-ls-triton}"

# ------------------------------------------------------------ eval knobs ----
export LIMIT="${LIMIT:-608}"     # questions per benchmark; lower it to smoke-test
export BS="${BS:-8}"             # batch size; lower if you run out of VRAM
export SHARDS="${SHARDS:-4}"     # parallel shards, one per GPU
export MAXNEW="${MAXNEW:-2048}"  # generation cap. The 27B needs 4096 -- see
                                 # START_HERE.txt, "the truncation trap".

# Default skills per benchmark. One canonical file per benchmark. LiveMath's is
# strength_audit.md since 2026-10-05; compare_claims (v1-v3) is archived in
# skills/archive/ (see skills/notes/README.md).
export SKILL_LIVEMATH="${SKILL_LIVEMATH:-strength_audit.md}"
export SKILL_SPREADSHEET="${SKILL_SPREADSHEET:-spreadsheet_edit.md}"
export SKILL_OFFICEQA="${SKILL_OFFICEQA:-officeqa_lookup.md}"
export SKILL_PLACEBO="${SKILL_PLACEBO:-placebo_matched.md}"

# Where the agent harness reaches its model (served separately; see
# 00_setup/05_serve_model.sh).
export LLM_BASE_URL="${LLM_BASE_URL:-http://127.0.0.1:9000}"
export LLM_API_KEY="${LLM_API_KEY:-sk-anything}"
