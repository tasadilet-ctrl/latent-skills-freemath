#!/usr/bin/env bash
# Install SkillOpt (microsoft/SkillOpt, MIT) at the commit every run here used.
#   ./setup.sh [work dir]        default: $HOME/skillopt_work
# Needs uv (https://docs.astral.sh/uv/). The vLLM servers come from a separate
# env (VLLM_ENV in run_skillopt.sbatch); this venv only runs the optimizer loop.
set -euo pipefail
W=${1:-$HOME/skillopt_work}; COMMIT=343db22
mkdir -p "$W/logs" "$W/outputs"
[ -d "$W/SkillOpt" ] || git clone https://github.com/microsoft/SkillOpt.git "$W/SkillOpt"
cd "$W/SkillOpt" && git checkout -q $COMMIT
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e . json_repair   # json_repair: the local optimizer's JSON needs it
echo "SkillOpt $COMMIT ready in $W/SkillOpt"
