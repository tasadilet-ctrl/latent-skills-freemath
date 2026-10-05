#!/usr/bin/env bash
# Download model weights into the shared cache.
#
#   ./00_setup/03_model_weights.sh                  the default (Qwen3-8B)
#   MODEL_ID=Qwen/Qwen3-14B   ./00_setup/03_model_weights.sh
#   MODEL_ID=Qwen/Qwen3.6-27B ./00_setup/03_model_weights.sh
#   ./00_setup/03_model_weights.sh all              all three (~110 GB)
#
# Sizes, so nothing surprises you: 8B ~16 GB, 14B ~28 GB, 27B ~60 GB.
# They land in $HF_HOME (default $KIT/.hf_cache). Point HF_HOME at an existing
# cache to avoid re-downloading weights you already have.
set -uo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$KIT/lib/common.sh"
require_env "$PY_EVAL" eval

MODELS=("$MODEL_ID")
[ "${1:-}" = all ] && MODELS=(Qwen/Qwen3-8B Qwen/Qwen3-14B Qwen/Qwen3.6-27B)

df_free() { df -BG --output=avail "$HF_HOME" 2>/dev/null | tail -1 | tr -dc '0-9'; }
say "Cache: $HF_HOME   (free: $(df_free) GB)"

for m in "${MODELS[@]}"; do
  say "Fetching $m"
  MODEL_ID="$m" "$PY_EVAL" - <<'PY' || fail "download failed for $m"
import os
from huggingface_hub import snapshot_download
m = os.environ["MODEL_ID"]
p = snapshot_download(m, allow_patterns=["*.json","*.safetensors","*.txt","*.model"])
print("   ", m, "->", p)
PY
done

say "Weights ready"
note "next: ./00_setup/04_smoke_test.sh"
