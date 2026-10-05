#!/usr/bin/env bash
# One table across every axis: benchmark x harness x model x condition.
#
#   ./full_matrix.sh
#   ./full_matrix.sh > ../RESULTS_MATRIX.txt
#
# This is the view to read before drawing any conclusion, because it puts the
# controlled and uncontrolled embedding arms next to each other and next to
# the CONTROL.
#
# HARNESS IS A SEPARATE ROW, NOT A DETAIL. OpenHands and Strands do not give
# the agent the same tools, names or error text, so their cells are not
# comparable and are never merged. Runs predating 2026-10-05 carry no harness
# field and are labelled openhands.
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"
require_env "$PY_EVAL" eval
exec "$PY_EVAL" "$KIT/src/matrix.py" "$@"
