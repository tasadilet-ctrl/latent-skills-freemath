#!/usr/bin/env bash
# Build the three virtualenvs this project needs.
#
#   ./00_setup/01_python_envs.sh
#
# Safe to re-run: existing envs are reused and only missing packages installed.
#
#   CUDA=cu126 ./00_setup/01_python_envs.sh   force a torch build
#   SKIP_AGENT=1 ...                          skip the agent env (LiveMath only)
#
# WHY THREE ENVIRONMENTS, not one:
#   .venv       torch + transformers. Everything that loads weights locally:
#               the direct benchmarks, vector extraction, fidelity, the hooked
#               server.
#   .agentvenv  strands-agents. Needs python >=3.10 and drags in its own
#               openai/anthropic tree. Installed next to torch it has, in
#               practice, reinstalled torch from under the eval env.
#   .plotvenv   matplotlib alone. A plotting stack pinned beside a CUDA stack
#               is the classic way to end up with a numpy that satisfies
#               neither.
set -uo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$KIT/lib/common.sh"

# ------------------------------------------------------------- interpreter --
say "Looking for a Python interpreter (need 3.10+)"
PY_BIN=""
for c in python3.12 python3.11 python3.10 python3 python; do
  command -v "$c" >/dev/null 2>&1 || continue
  v=$("$c" -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null) || continue
  maj=${v%%.*}; min=${v##*.}
  if [ "$maj" -eq 3 ] && [ "$min" -ge 10 ]; then PY_BIN="$c"; note "using $c (python $v)"; break; fi
done
# This bit is not paranoia: the autoPET run on this same cluster silently built
# itself on the system python 3.9 and only failed much later.
[ -n "$PY_BIN" ] || fail "no python 3.10+ found. Load a module (module avail python) or install one."

# -------------------------------------------------------------- torch wheel --
say "Choosing a PyTorch build"
DRIVER_CUDA=""
if command -v nvidia-smi >/dev/null 2>&1; then
  DRIVER_CUDA=$(nvidia-smi 2>/dev/null | grep -oE 'CUDA Version: [0-9]+\.[0-9]+' | head -1 | awk '{print $3}')
fi
if [ -n "${CUDA:-}" ]; then TORCH_IDX="$CUDA"
elif [ -z "$DRIVER_CUDA" ]; then TORCH_IDX="cu128"; warn "no nvidia-smi; guessing cu128"
else
  maj=${DRIVER_CUDA%%.*}; min=${DRIVER_CUDA##*.}
  if   [ "$maj" -ge 13 ]; then TORCH_IDX="cu128"
  elif [ "$maj" -eq 12 ] && [ "$min" -ge 8 ]; then TORCH_IDX="cu128"
  elif [ "$maj" -eq 12 ] && [ "$min" -ge 6 ]; then TORCH_IDX="cu126"
  elif [ "$maj" -eq 12 ]; then TORCH_IDX="cu121"
  else fail "CUDA $DRIVER_CUDA is older than this project supports (need 12.x+)"; fi
  note "driver CUDA $DRIVER_CUDA -> $TORCH_IDX wheels"
fi

# ------------------------------------------------------------------- build --
mkenv() {
  local path="$1"
  [ -d "$path" ] && { note "$(basename "$path") exists, reusing"; return; }
  "$PY_BIN" -m venv "$path" || fail "could not create $path"
  "$path/bin/pip" install -q --upgrade pip setuptools wheel
  note "created $(basename "$path")"
}

say "1/3  eval environment (torch, transformers) -- the slow one"
mkenv "$KIT/.venv"
"$KIT/.venv/bin/python" -c "import torch" 2>/dev/null || \
  "$KIT/.venv/bin/pip" install -q torch --index-url "https://download.pytorch.org/whl/$TORCH_IDX" \
    || fail "torch install failed. Try CUDA=cu126 ./00_setup/01_python_envs.sh"
"$KIT/.venv/bin/pip" install -q -r "$KIT/requirements/eval.txt" || fail "eval deps failed"
note "ok: $("$KIT/.venv/bin/python" -c 'import torch;print("torch",torch.__version__,"cuda",torch.cuda.is_available())')"

if [ -z "${SKIP_AGENT:-}" ]; then
  say "2/3  agent environment (strands-agents)"
  mkenv "$KIT/.agentvenv"
  "$KIT/.agentvenv/bin/pip" install -q -r "$KIT/requirements/agent.txt" || fail "agent deps failed"
  note "ok: $("$KIT/.agentvenv/bin/python" -c 'import importlib.metadata as m;print("strands-agents",m.version("strands-agents"))')"
else
  note "2/3  agent environment SKIPPED (SKIP_AGENT=1)"
fi

say "3/3  plotting environment (matplotlib)"
mkenv "$KIT/.plotvenv"
"$KIT/.plotvenv/bin/pip" install -q -r "$KIT/requirements/plot.txt" || fail "plot deps failed"
note "ok"

say "Environments ready"
note "next: ./00_setup/02_benchmark_data.sh"
