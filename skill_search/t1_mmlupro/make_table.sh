#!/usr/bin/env bash
# Build the 5-run MMLU-Pro table (PNG + markdown) with Adil's make_runs_table_png.py.
# Usage: bash make_table.sh <work dir> [runs] [t1|t2]   (results are pulled from the box; nothing is committed)
#   t1 (default): train 40 / val 100 / test 365, results/, with the one-line and elimination prompt columns
#   t2: Adil's split train 100 / val 150 / test 255 (make_split_t2.py), 4 samples per val question, results_t2/
# Runs with any file missing are left out (the title says how many runs went in).
set -euo pipefail
S=${1:?work dir}; N=${2:-5}; EXP=${3:-t1}
if [ "$EXP" = t2 ]; then
  RES=results_t2; SPLITDIR=mmlupro_math_t2; COLS="4b 8b 14b 27b"; NTEST=255
  SETUP="train 100 / val 150 (each val question scored 4 times, averaged), batch 100, 4 epochs"
  ONE=""; ONE2=""
else
  RES=results; SPLITDIR=mmlupro_math_tq_sb; COLS="oneliner elim 4b 8b 14b 27b"; NTEST=365
  SETUP="train 40 / val 100 from the pre-registered split"
  ONE="One-line prompt: 'Solve the task step by step and check your work before answering.' as the system prompt, no training; not in the average column."
  ONE2="Elimination prompt: 'Reason step by step. Before answering, read all the options and eliminate those that contradict your result or the question's conditions; check units and signs. Then give the remaining option.' No training; not in the average column."
fi
REPO=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
BOX=adilet_tasbolat@100.85.184.12
mkdir -p "$S/src" "$S/res/results" "$S/out"
for f in make_runs_table_png make_table_png matrix; do git -C "$REPO" show origin/adil:src/$f.py > "$S/src/$f.py"; done
touch "$S/src/__init__.py"
# Local tweak to Adil's script: the one-liner prompt is a control column next to the baseline, labelled as
# such and left out of the "average (skill columns)" column.
python3 - "$S/src/make_runs_table_png.py" <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
s = s.replace("for c in cols[1:]]", "for c in cols[1:] if c not in CONTROLS]")
s = s.replace('**{s: f"{s.upper()}-27B skill" for s in a.skills}}',
              '**{s: f"{s.upper()}-27B skill" for s in a.skills}, "oneliner": "one-line prompt\\n(no training)", "elim": "elimination prompt\\n(no training)"}')
s = s.replace("\ndef render(", "\nCONTROLS = {\"oneliner\", \"elim\"}\n\n\ndef render(", 1)
assert s.count("if c not in CONTROLS]") == 2 and "CONTROLS = {" in s and "one-line prompt" in s
open(p, "w").write(s)
PY
rm -rf "$S/res/results"; mkdir -p "$S/res/results"
rsync -az -e "ssh -o ConnectTimeout=30" $BOX:t1_mq/$RES/ "$S/res/results/"
ssh -o ConnectTimeout=30 $BOX "cat ~/skillopt_work/mq_split/$SPLITDIR/test/items.json" \
  | python3 -c 'import json,sys; print(json.dumps([x["id"] for x in json.load(sys.stdin)]))' > "$S/heldout_ids.json"
cd "$S"
NOTES=(--note "Each run: the named model answers, Qwen3.6-27B edits (both T 1.0), $SETUP; then baseline + that run's 4 skills on every model."
       --note "Answers: vLLM (FlashInfer), T 1.0 (top_p 1), seed = run, thinking off, 2048 tokens (27B 4096). Scored on the $NTEST held-out test questions.")
[ -n "$ONE" ] && NOTES+=(--note "$ONE")
[ -n "$ONE2" ] && NOTES+=(--note "$ONE2")
python3 -m src.make_runs_table_png --results-dir res/results --prefix mmlupro_math_tq_sb --score-key em \
  --ids heldout_ids.json --runs "$N" --skills $COLS \
  --title "MMLU-Pro math ($EXP): SkillOpt skills at temperature 1.0" "${NOTES[@]}" \
  --out-dir "$S/out" --stem results_table_mmlupro_$EXP
