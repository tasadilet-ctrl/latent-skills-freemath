#!/usr/bin/env bash
# Build the 5-run MMLU-Pro table (PNG + markdown) with Adil's make_runs_table_png.py.
# Usage: bash make_table.sh <work dir> [runs]   (results are pulled from the box; nothing is committed)
set -euo pipefail
S=${1:?work dir}; N=${2:-5}
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
              '**{s: f"{s.upper()}-27B skill" for s in a.skills}, "oneliner": "one-line prompt\\n(no training)"}')
s = s.replace("\ndef render(", "\nCONTROLS = {\"oneliner\"}\n\n\ndef render(", 1)
assert s.count("if c not in CONTROLS]") == 2 and "CONTROLS = {" in s and "one-line prompt" in s
open(p, "w").write(s)
PY
rsync -az -e "ssh -o ConnectTimeout=30" $BOX:t1_mq/results/ "$S/res/results/"
ssh -o ConnectTimeout=30 $BOX 'python3 -c "import json,os;it=json.load(open(os.path.expanduser(\"~/skillopt_work/mq_split/mmlupro_math_tq_sb/test/items.json\")));print(json.dumps([x[\"id\"] if isinstance(x,dict) else x for x in it]))"' > "$S/heldout_ids.json"
cd "$S"
python3 -m src.make_runs_table_png --results-dir res/results --prefix mmlupro_math_tq_sb --score-key em \
  --ids heldout_ids.json --runs "$N" --skills oneliner 4b 8b 14b 27b \
  --title "MMLU-Pro math: SkillOpt skills at temperature 1.0" \
  --note "Each run: the named model answers, Qwen3.6-27B edits (both T 1.0), train 40 / val 100 from the pre-registered split; then baseline + that run's 4 skills on every model." \
  --note "Answers: vLLM (FlashInfer), T 1.0 (top_p 1), seed = run, thinking off, 2048 tokens (27B 4096). Scored on the 365 held-out test questions." \
  --note "One-line prompt: 'Solve the task step by step and check your work before answering.' as the system prompt, no training; not in the average column." \
  --out-dir "$S/out" --stem results_table_mmlupro_t1
