#!/usr/bin/env bash
# Queued after the mcqmath run: SkillOpt on IMO-AnswerBench (Qwen3-8B) and ArxivMath (Qwen3-14B target),
# then forced final evals, rescoring, and a report. Same freemath pipeline as BeyondAIME/HARDMath2/RealMath.
set -uo pipefail
W=$HOME/skillopt_work; K=$W/kit_v4/freemath
until grep -q "\[mqall\] ALL_DONE" $W/logs/mq_all.log 2>/dev/null; do
  tmux has-session -t mqfull 2>/dev/null || { echo "[next] mqfull gone without ALL_DONE, stopping"; exit 1; }
  sleep 120
done
$K/install_env.sh $W/SkillOpt
source $W/gpu_wait.sh; $K/run_freemath_local.sh Qwen/Qwen3-8B imoanswer
source $W/gpu_wait.sh; $K/run_freemath_local.sh Qwen/Qwen3-14B arxivmath
source $W/gpu_wait.sh; $K/run_final_forced.sh Qwen/Qwen3-8B imoanswer
source $W/gpu_wait.sh; $K/run_final_forced.sh Qwen/Qwen3-14B arxivmath
cd $W/SkillOpt
for t in qwen3-8b qwen3-14b; do .venv/bin/python $K/rescore_freemath.py $W $t; done
{ .venv/bin/python $K/analyze_freemath.py $W qwen3-8b final_eval_forced; .venv/bin/python $K/analyze_freemath.py $W qwen3-14b final_eval_forced; } 2>&1 \
  | grep -v -iE "warning|timeout is disabled|interuption" > $W/fm_next_report.txt
echo "[next] ALL_DONE"
