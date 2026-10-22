#!/usr/bin/env bash
# After rerun_v4.sh: final tables (unforced + forced, rescored) and learned skills in one folder.
set -uo pipefail
W=$HOME/skillopt_work; K=$W/kit_v4/freemath; R=$W/fm_results
until grep -q "\[v4\] ALL_DONE" $W/logs/fm_v4.log 2>/dev/null; do
  tmux has-session -t fmv4 2>/dev/null || { echo "[report] fmv4 is gone without ALL_DONE, stopping"; exit 1; }
  sleep 120
done
mkdir -p $R/skills
cd $W/SkillOpt
{ echo "# freemath SkillOpt results, Qwen3-8B target, $(date)"
  for d in final_eval final_eval_forced; do .venv/bin/python $K/analyze_freemath.py $W qwen3-8b $d; done
} 2>&1 | grep -v -iE "warning|timeout is disabled|interuption" > $R/report.txt
for b in beyondaime hardmath2 realmath; do
  O=$W/outputs/fm_${b}_qwen3-8b
  [ -f $O/best_skill.md ] && cp $O/best_skill.md $R/skills/${b}_best_skill.md
  [ -f $O/summary.json ] && cp $O/summary.json $R/skills/${b}_summary.json
  [ -f $O/history.json ] && cp $O/history.json $R/skills/${b}_history.json
done
echo "[report] DONE -> $R"; cat $R/report.txt
