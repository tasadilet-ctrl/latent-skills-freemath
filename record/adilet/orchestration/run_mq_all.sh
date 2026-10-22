#!/usr/bin/env bash
# mcqmath: smoke (plumbing), then the full SkillOpt runs + final comparison, then the report.
set -uo pipefail
W=$HOME/skillopt_work; K=$W/kit_mq/mcqmath
SMOKE=1 $K/run_mcqmath_local.sh Qwen/Qwen3-8B mmlupro_math_tq_sb 2>&1 | tee $W/logs/mq_smoke.log
grep -q "BENCH_DONE" $W/logs/mq_smoke.log || { echo "[mqall] SMOKE_FAILED"; exit 1; }
echo "[mqall] smoke ok"
$K/run_mcqmath_local.sh Qwen/Qwen3-8B mmlupro_math_tq_sb supergpqa_math_hard
cd $W/SkillOpt && .venv/bin/python $K/analyze_mcqmath.py $W qwen3-8b | tee $W/mq_report.txt
echo "[mqall] ALL_DONE"
