#!/usr/bin/env bash
# OPTIONAL CHECK -- does the model actually FOLLOW the skill, or just have it?
#
#   ./06_check_skill_compliance.sh
#
# Presence in the prompt is trivially verifiable by tokenising (410 tokens vs
# 36). Compliance is not. If generations under the skill look like generations
# under the placebo, then the "target behaviour" the embedding skill is being
# asked to reproduce barely differs from baseline -- and every fidelity number
# downstream is measuring noise.
#
# Prints all three conditions side by side for eyeballing, plus a marker count
# for the procedure's observable surface. Run it once per (model, skill) pair
# before trusting a fidelity sweep.
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_EVAL" eval
NO_SHARD=1 SHARDS=1 submit "compliance_${MODEL_TAG}" "$PY_EVAL" "$KIT/src/compliance_check.py"
