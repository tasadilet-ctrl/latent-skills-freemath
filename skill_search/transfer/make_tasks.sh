#!/usr/bin/env bash
# Math-skill transfer to OfficeQA (text-only, cited pages in the prompt) and
# SpreadsheetBench (single-turn). Writes, for ONE skill:
#   extract_<stem>.txt   2 vectors per model from the NEUTRAL pool (n=50):
#                          _placebo  = [placebo + skill] - [placebo]   (ES vs placebo)
#                          _plain    = [skill] - [nothing]             (ES vs nothing)
#   eval_<stem>.txt      per model and benchmark: text, ES vs placebo, ES vs nothing
#                        (+ OfficeQA baselines with --baselines; SpreadsheetBench
#                         baselines already exist in results/)
# usage: ./make_tasks.sh <skill.md> <placebo.md> [--baselines]
# Operating points as on LiveMath: 8B L34, 14B L37, 27B L62, gamma 0.3 relative.
KIT=$(cd "$(dirname "$0")/../.." && pwd); V=$KIT/vectors
SK=$(realpath "$1"); PL=$(realpath "$2"); STEM=$(basename "$SK" .md); BL=${3:-}
X=extract_$STEM.txt; E=eval_$STEM.txt; : > $X; : > $E
# model tag layer oqa_tokens sb_tokens oqa_bs sb_bs oqa_shards sb_shards
for spec in "Qwen/Qwen3-8B qwen3-8b 34 2048 1536 8 4 2 2" \
            "Qwen/Qwen3-14B qwen3-14b 37 2048 1536 8 4 2 2" \
            "Qwen/Qwen3.6-27B qwen3.6-27b 62 4096 2048 4 4 4 4"; do
  set -- $spec; M=$1; T=$2; L=$3; OT=$4; ST=$5; OB=$6; SB=$7; OK=$8; SKN=$9
  XC="MODEL_ID=$M python $KIT/src/extract_vectors.py --pool neutral --n 50 --skill $SK"
  echo "$XC --baseline-skill $PL --out $V/v_${T}_${STEM}_neutral_n50_placebo.pt" >> $X
  echo "$XC --out $V/v_${T}_${STEM}_neutral_n50_plain.pt" >> $X
  O="MODEL_ID=$M python $KIT/src/evaluate.py --domain officeqa --limit 0 --batch-size $OB --max-new-tokens $OT"
  S="MODEL_ID=$M python $KIT/src/evaluate_spreadsheet.py --limit 400 --batch-size $SB --max-new-tokens $ST"
  EMB="--layers $L --gamma 0.3 --mode relative"
  for i in $(seq 0 $((OK-1))); do
    [ "$BL" = "--baselines" ] && echo "$O --condition baseline --shard $i/$OK" >> $E
    echo "$O --condition text --skill $SK --shard $i/$OK" >> $E
    for k in placebo plain; do echo "$O --condition embed --vectors $V/v_${T}_${STEM}_neutral_n50_$k.pt $EMB --shard $i/$OK" >> $E; done
  done
  for i in $(seq 0 $((SKN-1))); do
    echo "$S --condition text --skill $SK --shard $i/$SKN" >> $E
    for k in placebo plain; do echo "$S --condition embed --vectors $V/v_${T}_${STEM}_neutral_n50_$k.pt $EMB --shard $i/$SKN" >> $E; done
  done
done
wc -l $X $E
