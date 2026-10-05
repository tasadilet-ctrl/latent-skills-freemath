#!/usr/bin/env bash
# setup.sh -- one-time setup. Runs everything in 00_setup/ in order.
#
#     ./setup.sh
#
# Safe to re-run: every step skips what is already done. If one fails, fix the
# cause and run it again -- it picks up where it left off.
#
# Takes roughly 30-60 min, nearly all of it downloading torch and the model.
#
#   SKIP_MODEL=1 ./setup.sh        environments and data only
#   SKIP_AGENT=1 ./setup.sh        skip the Strands env (LiveMath only)
#   MODEL_ID=Qwen/Qwen3-14B ./setup.sh
#   HF_TOKEN=hf_... ./setup.sh     needed for OfficeQA (gated dataset)
#
# To run the individual steps yourself instead, they are in 00_setup/ and each
# one works standalone.
set -uo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$KIT"

printf '\n\033[1m=== latent-skills kit: setup ===\033[0m\n'
printf '    kit at: %s\n' "$KIT"

step() {
  printf '\n\033[1m--- %s ---\033[0m\n' "$1"; shift
  "$@" || { printf '\n\033[1;31msetup stopped at: %s\033[0m\n' "$1" >&2; exit 1; }
}

step "1/4  python environments"  ./00_setup/01_python_envs.sh
step "2/4  benchmark data"       ./00_setup/02_benchmark_data.sh

if [ -n "${SKIP_MODEL:-}" ]; then
  printf '\n--- 3/4  model weights SKIPPED (SKIP_MODEL=1) ---\n'
else
  step "3/4  model weights"      ./00_setup/03_model_weights.sh
fi

step "4/4  smoke test"           ./00_setup/04_smoke_test.sh

cat <<'DONE'

================================================================================
 SETUP COMPLETE
================================================================================
Read START_HERE.txt next -- in particular "the three traps", which covers the
three failure modes that produced wrong numbers in this project and left no
error in any log.

The shortest useful thing to run now:

    01_livemath_direct/run_baseline.sh
    01_livemath_direct/run_text_skill.sh
    06_reports/results_table.sh

================================================================================
DONE
