#!/usr/bin/env bash
set -uo pipefail
W=$HOME/skillopt_work; K=$W/kit_mq/mcqmath
source $W/gpu_wait.sh
$K/run_mcqmath_local.sh Qwen/Qwen3-8B mmlupro_math_tq_sb supergpqa_math_hard
cd $W/SkillOpt && .venv/bin/python $K/analyze_mcqmath.py $W qwen3-8b | tee $W/mq_report.txt
echo "[mqall] ALL_DONE"
