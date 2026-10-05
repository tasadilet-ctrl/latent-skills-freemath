#!/usr/bin/env bash
# The per-benchmark table: accuracy, CI, paired McNemar vs that row's baseline.
#
#   ./results_table.sh
#   ./results_table.sh > ../RESULTS_TABLE.txt
#
# Merges every shard in ../results/ and prints one block per
# (benchmark, model). Columns:
#
#   acc %       exact-match. On LiveMath chance is 20%.
#   95% CI      Wilson interval.
#   n           MUST be the full benchmark size. 456 instead of 608 means a
#               shard died and the cell is incomplete.
#   parse       fraction of replies that committed to an answer. Below 1.000
#               the cell is partly measuring verbosity, not correctness.
#   d vs base   points against this model's own baseline.
#   McNemar p   PAIRED test, because both conditions answer the identical
#               items. An unpaired two-proportion test throws that pairing
#               away and needs a far larger effect to detect anything.
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_EVAL" eval
exec "$PY_EVAL" "$KIT/src/report.py" "$@"
