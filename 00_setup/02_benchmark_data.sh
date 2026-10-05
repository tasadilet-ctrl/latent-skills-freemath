#!/usr/bin/env bash
# Download and prepare the benchmark data.
#
#   ./00_setup/02_benchmark_data.sh            all three
#   ./00_setup/02_benchmark_data.sh livemath   just one
#
# ALL THREE DOWNLOAD. Two need no credentials at all; OfficeQA needs a
# Hugging Face token because its document corpus is gated.
#
#   LiveMath          LiveMathematicianBench/LiveMathematicianBench   ungated
#   SpreadsheetBench  KAKA22/SpreadsheetBench (verified-400)          ungated
#   OfficeQA          databricks/officeqa                             GATED
#
# Nothing is redistributed with this repository -- these are third-party
# benchmarks carrying answer keys, and OfficeQA's licence does not permit it.
# See DATA.md. Everything lands in data/ and is gitignored.
#
# Safe to re-run: each step skips what is already present.
set -uo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$KIT/lib/common.sh"
WHICH="${1:-all}"
cd "$DATA"

HF="https://huggingface.co/datasets"

# ------------------------------------------------------------------ LiveMath --
# 608 research-level questions across 8 monthly releases. The benchmark is
# "live": each month adds questions drawn from arXiv papers published after
# the models' training cutoffs, which is what makes it contamination-resistant.
# We pin the 8 months the reported cells used (202511-202606) so the set does
# not silently grow under a re-run.
LM_MONTHS="202511 202512 202601 202602 202603 202604 202605 202606"

if [ "$WHICH" = all ] || [ "$WHICH" = livemath ]; then
  say "LiveMath"
  if [ -s "$DATA/livemath.jsonl" ]; then
    note "already prepared: $(wc -l < "$DATA/livemath.jsonl") questions"
  else
    missing=0
    for m in $LM_MONTHS; do [ -s "$DATA/lm_$m.json" ] || missing=$((missing+1)); done
    if [ "$missing" -gt 0 ]; then
      note "fetching $missing of 8 monthly files (~4 MB, no token needed)"
      for m in $LM_MONTHS; do
        [ -s "$DATA/lm_$m.json" ] && continue
        url="$HF/LiveMathematicianBench/LiveMathematicianBench/resolve/main/data/$m/qa_${m}_final.json"
        curl -fsSL "$url" -o "$DATA/lm_$m.json.part" \
          && mv "$DATA/lm_$m.json.part" "$DATA/lm_$m.json" \
          && note "  $m ok" \
          || { rm -f "$DATA/lm_$m.json.part"; fail "could not fetch $m from $url"; }
      done
    fi
    require_env "$PY_EVAL" eval
    # The prepare step is NOT cosmetic. In the raw files the correct choice is
    # labelled 'A' in all 608 questions -- the letters encode canonical roles
    # (A=correct, C=weaker-true, D=wildcard trap), not a presentation order.
    # Unshuffled, "always answer A" scores 100%.
    "$PY_EVAL" "$DATA/prepare_livemath.py" || fail "LiveMath prep failed"
  fi
  n=$(wc -l < "$DATA/livemath.jsonl")
  [ "$n" -eq 608 ] || warn "expected 608 questions, found $n -- results will not match the published cells"
fi

# ---------------------------------------------------------- SpreadsheetBench --
# The upstream "Verified 400" release (Dec 2025), downloaded byte-identical.
# This project then excludes 2 tasks that are not gradeable; those ids live in
# data/sb400_exclusions.json and are re-applied here, so the whole subset is
# reproducible from a public download rather than a file someone emails you.
if [ "$WHICH" = all ] || [ "$WHICH" = spreadsheet ]; then
  say "SpreadsheetBench"
  if [ -d "$DATA/spreadsheetbench_verified_400/spreadsheet" ]; then
    note "already here: $(ls "$DATA/spreadsheetbench_verified_400/spreadsheet" | wc -l) task directories"
  else
    if [ ! -s "$DATA/sb400.tar.gz" ]; then
      note "fetching the verified-400 subset (15 MB, no token needed)"
      curl -fsSL "$HF/KAKA22/SpreadsheetBench/resolve/main/spreadsheetbench_verified_400.tar.gz" \
        -o "$DATA/sb400.tar.gz.part" \
        && mv "$DATA/sb400.tar.gz.part" "$DATA/sb400.tar.gz" \
        || { rm -f "$DATA/sb400.tar.gz.part"
             fail "SpreadsheetBench download failed.
    Mirror: https://github.com/RUCKBReasoning/SpreadsheetBench -> data/spreadsheetbench_verified_400.tar.gz"; }
    fi
    tar xzf "$DATA/sb400.tar.gz" -C "$DATA" || fail "could not unpack sb400.tar.gz"
    note "unpacked $(ls "$DATA/spreadsheetbench_verified_400/spreadsheet" | wc -l) task directories"
  fi

  # Verify, do not patch. The 2 excluded tasks ship excluded by upstream, so
  # there is nothing to apply -- but if a re-download ever differs from what
  # the reported cells ran against, every SpreadsheetBench number moves with
  # no error anywhere. Check it.
  require_env "$PY_EVAL" eval
  "$PY_EVAL" - <<'PY' || warn "SpreadsheetBench integrity check could not run"
import json, os, sys
d = os.environ["DATA"]
exp = json.load(open(os.path.join(d, "sb400_expected.json")))
tasks = json.load(open(os.path.join(d, "spreadsheetbench_verified_400", "dataset.json")))
got = {t["id"] for t in tasks if "exclude" in t}
want = {e["id"] for e in exp["exclusions"]}
ok = len(tasks) == exp["n_tasks"] and got == want
print(f"    {len(tasks)} tasks, {len(got)} excluded -> effective n = {len(tasks)-len(got)}")
if not ok:
    print(f"    !! UPSTREAM HAS CHANGED: expected {exp['n_tasks']} tasks and "
          f"exclusions {sorted(want)}, found {len(tasks)} and {sorted(got)}")
    print("    !! numbers from this data will NOT match the reported cells")
    sys.exit(1)
print("    matches the release the reported cells used")
PY
fi

# ------------------------------------------------------------------ OfficeQA --
if [ "$WHICH" = all ] || [ "$WHICH" = officeqa ]; then
  say "OfficeQA"
  if [ -d "$DATA/officeqa_docs" ] && [ "$(ls "$DATA/officeqa_docs" | wc -l)" -gt 200 ]; then
    note "already here: $(ls "$DATA/officeqa_docs" | wc -l) bulletins"
  else
    # The 246-question manifest is open; the Treasury bulletin corpus it
    # grounds on is gated by Databricks (gated: auto -- approval is instant,
    # but it must be accepted once per account). Each file is checked against
    # the manifest's sha256, so a silently-changed upstream cannot pass.
    if [ -z "${HF_TOKEN:-}" ] && [ ! -s "$HOME/.cache/huggingface/token" ]; then
      fail "OfficeQA needs a Hugging Face token.

    Its document corpus is gated (databricks/officeqa). Approval is automatic,
    but you must accept the terms once with your own account:

      1. open https://huggingface.co/datasets/databricks/officeqa
      2. accept the terms
      3. export HF_TOKEN=hf_...   (or run: huggingface-cli login)
      4. re-run this script

    The other two benchmarks need no token:
        ./00_setup/02_benchmark_data.sh livemath
        ./00_setup/02_benchmark_data.sh spreadsheet"
    fi
    note "fetching ~146 MB of Treasury bulletins"
    require_env "$PY_EVAL" eval
    "$PY_EVAL" "$DATA/prepare_officeqa.py" || fail "OfficeQA prep failed.
    If it 401'd, the terms have not been accepted for the account behind
    HF_TOKEN -- see https://huggingface.co/datasets/databricks/officeqa"
  fi
  # Four bulletins changed upstream after the manifest was written; the 7
  # questions grounded on them are excluded by run_oqa_agent.py.
  note "4 bulletins are tainted -- 239 of 246 questions are scored"
fi

say "Data ready"
note "next: ./00_setup/03_model_weights.sh"
