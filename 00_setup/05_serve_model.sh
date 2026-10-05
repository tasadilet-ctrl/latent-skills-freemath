#!/usr/bin/env bash
# Serve a model over an OpenAI-compatible HTTP API, for the AGENT benchmarks.
#
#   ./00_setup/05_serve_model.sh plain          vLLM -- baseline and text arms
#   ./00_setup/05_serve_model.sh steered <vec> <layers> <gamma>
#                                               hooked HF server -- embed arms
#
# WHY THIS EXISTS AT ALL
#   The direct benchmarks (LiveMath) load weights in-process. The agent
#   benchmarks do not: the Strands harness talks HTTP, so something has to be
#   serving. Start this first, in its own terminal or its own SLURM job, then
#   run the cell.
#
# WHY TWO SERVERS
#   vLLM is fast but exposes no residual stream, so it cannot do the embedding
#   arm at all. src/serve_hooked.py is plain HF transformers with the steering
#   hooks behind the same API -- far slower (serial), but it is the only way
#   an embed cell can run through an agent.
#
# ===========================================================================
#  THE TOOL-CALL PARSER TRAP -- read this before you run an agent cell
# ===========================================================================
#   vLLM needs --enable-auto-tool-choice and a --tool-call-parser matched to
#   the MODEL GENERATION. Get it wrong and vLLM returns tool_calls: [], the
#   agent executes nothing, and the cell scores EXACTLY 0% with no error in
#   any log. It cost three runs and two wrong capability conclusions.
#
#       Qwen3-8B, Qwen3-14B  ->  hermes      (they emit Hermes JSON)
#       Qwen3.6-27B          ->  qwen3_xml
#
#   This script picks it from MODEL_ID. Override with PARSER=... if you know
#   better, but check the first episode's log for an actual tool call before
#   trusting a number.
# ===========================================================================
set -uo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$KIT/lib/common.sh"
require_env "$PY_EVAL" eval
MODE="${1:-plain}"
PORT="${PORT:-9000}"

case "$MODEL_ID" in
  *Qwen3.6*) DEFAULT_PARSER=qwen3_xml ;;
  *)         DEFAULT_PARSER=hermes    ;;
esac
PARSER="${PARSER:-$DEFAULT_PARSER}"

if [ "$MODE" = plain ]; then
  say "vLLM serving $MODEL_ID on :$PORT  (tool-call parser: $PARSER)"
  command -v vllm >/dev/null 2>&1 || "$PY_EVAL" -c "import vllm" 2>/dev/null \
    || fail "vLLM is not installed in the eval env.
    pip install vllm  into $KIT/.venv, or point LLM_BASE_URL at a server you already run."
  exec "$PY_EVAL" -m vllm.entrypoints.openai.api_server \
      --model "$MODEL_ID" --served-model-name "${MODEL_ID##*/}" \
      --host 0.0.0.0 --port "$PORT" \
      --enable-auto-tool-choice --tool-call-parser "$PARSER" \
      --reasoning-parser qwen3 \
      --tensor-parallel-size "${SLURM_GPUS:-1}"

elif [ "$MODE" = steered ]; then
  VEC="${2:?usage: 05_serve_model.sh steered <vectors.pt> <layers> <gamma>}"
  LAYERS="${3:?need layers, e.g. 34}"
  GAMMA="${4:?need gamma, e.g. 0.3}"
  [ -f "$VEC" ] || VEC="$VECTORS/$(basename "$VEC")"
  [ -f "$VEC" ] || fail "no such vector file: $VEC"
  say "hooked HF server: $MODEL_ID + $(basename "$VEC") L$LAYERS g$GAMMA on :$PORT"
  warn "this is the SLOW path (serial, no batching). A 400-task agent cell"
  warn "took ~25 h here against ~1 h for the single-turn arm."
  note "the adapters read /health to detect steering, so an embed cell cannot"
  note "be mistaken for a baseline in the results -- that bug cost a cell once."
  exec "$PY_EVAL" "$KIT/src/serve_hooked.py" \
      --port "$PORT" --served-name "${MODEL_ID##*/}" \
      --vectors "$VEC" --layers "$LAYERS" --gamma "$GAMMA" --mode relative

else
  fail "unknown mode '$MODE' -- expected 'plain' or 'steered'"
fi
