#!/usr/bin/env bash
# Fetch and prepare the benchmark data.
#
#   ./00_setup/02_benchmark_data.sh            all three
#   ./00_setup/02_benchmark_data.sh livemath   just one
#
# NO BENCHMARK DATA IS REDISTRIBUTED WITH THIS REPOSITORY. See DATA.md.
#   OfficeQA is a gated dataset, and all three files hold questions WITH
#   answer keys -- publishing those contaminates the benchmarks. Only the
#   preparation code ships.
#
#   SpreadsheetBench and OfficeQA download here. LiveMath cannot: it is built
#   from monthly raw files obtained from the benchmark authors, which this
#   script will tell you about if they are missing.
set -uo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$KIT/lib/common.sh"
WHICH="${1:-all}"
cd "$DATA"

# ------------------------------------------------------------------ LiveMath --
if [ "$WHICH" = all ] || [ "$WHICH" = livemath ]; then
  say "LiveMath"
  if [ -s "$DATA/livemath.jsonl" ]; then
    note "already here: $(wc -l < "$DATA/livemath.jsonl") questions"
  else
    # LiveMath has no public downloader: it is built from monthly raw files
    # supplied by the benchmark authors. Say so plainly rather than failing
    # inside a glob that matched nothing.
    if ! ls "$DATA"/lm_20*.json >/dev/null 2>&1; then
      fail "LiveMath raw files are missing.

    prepare_livemath.py builds data/livemath.jsonl from data/lm_20*.json
    (8 monthly files). They are not redistributed with this repository --
    obtain them from the benchmark authors and drop them in data/.

    See DATA.md. The other two benchmarks do not need them:
        ./00_setup/02_benchmark_data.sh spreadsheet
        ./00_setup/02_benchmark_data.sh officeqa"
    fi
    require_env "$PY_EVAL" eval
    "$PY_EVAL" "$DATA/prepare_livemath.py" || fail "LiveMath prep failed"
  fi
  n=$(wc -l < "$DATA/livemath.jsonl")
  [ "$n" -eq 608 ] || warn "expected 608 questions, found $n -- results will not match the published cells"
fi

# ---------------------------------------------------------- SpreadsheetBench --
if [ "$WHICH" = all ] || [ "$WHICH" = spreadsheet ]; then
  say "SpreadsheetBench"
  if [ -d "$DATA/spreadsheetbench_verified_400" ]; then
    note "already here: $(ls "$DATA/spreadsheetbench_verified_400" | wc -l) entries"
  else
    note "fetching ~22 MB of workbooks from Hugging Face"
    require_env "$PY_EVAL" eval
    "$PY_EVAL" - <<'PY' || fail "SpreadsheetBench fetch failed"
import os
from huggingface_hub import snapshot_download
d = os.environ["DATA"]
snapshot_download("RUCKBReasoning/SpreadsheetBench", repo_type="dataset",
                  local_dir=os.path.join(d, "spreadsheetbench_raw"))
print("    raw benchmark downloaded")
PY
    # BE HONEST ABOUT THE GAP. The raw benchmark is public and downloads
    # fine, but this project does not evaluate on the raw benchmark -- it
    # evaluates on a VERIFIED 400-TASK SUBSET, and the subset selection
    # (including which tasks are excluded) lives in a manifest,
    # spreadsheetbench_verified_400/dataset.json. No script in this
    # repository regenerates that manifest: it was produced once by checking
    # every task golden-vs-golden (394/394 passed, init-vs-golden
    # disagreement 0.3%) and the result was kept, not the procedure.
    warn "the raw benchmark is NOT what the reported cells used."
    warn "You also need spreadsheetbench_verified_400/dataset.json -- the"
    warn "subset manifest. It is not in this repository and is not"
    warn "regenerable from it. Ask the project owner for that directory."
    warn "See DATA.md."
  fi
fi

# ------------------------------------------------------------------ OfficeQA --
if [ "$WHICH" = all ] || [ "$WHICH" = officeqa ]; then
  say "OfficeQA"
  if [ -d "$DATA/officeqa_docs" ] && [ "$(ls "$DATA/officeqa_docs" | wc -l)" -gt 200 ]; then
    note "already here: $(ls "$DATA/officeqa_docs" | wc -l) bulletins"
  else
    note "fetching ~146 MB of Treasury bulletins"
    # databricks/officeqa is gated: auto. Someone must click through the terms
    # on the dataset page with the account whose HF_TOKEN is in the
    # environment, ONCE, or this 401s.
    [ -n "${HF_TOKEN:-}" ] || warn "HF_TOKEN is not set; a gated dataset will 401"
    require_env "$PY_EVAL" eval
    "$PY_EVAL" "$DATA/prepare_officeqa.py" || fail "OfficeQA prep failed.
    If it 401'd: open https://huggingface.co/datasets/databricks/officeqa,
    accept the terms with the same account as HF_TOKEN, then re-run."
  fi
  # Four bulletins changed upstream after the manifest was written; questions
  # grounded on them are excluded by run_oqa_agent.py unless --include-tainted.
  note "4 bulletins are excluded as tainted -- 239 of 246 questions are scored"
fi

say "Data ready"
note "next: ./00_setup/03_model_weights.sh"
