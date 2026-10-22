#!/usr/bin/env bash
# Re-run HARDMath2 + RealMath with the thread-safe scorer (kit_v4), then forced evals, then rescore.
set -uo pipefail
W=$HOME/skillopt_work; K=$W/kit_v4/freemath
$K/install_env.sh $W/SkillOpt
for b in hardmath2 realmath; do
  [ -d $W/outputs/fm_${b}_qwen3-8b ] && mv $W/outputs/fm_${b}_qwen3-8b $W/outputs/fm_${b}_qwen3-8b_bugged_scorer
done
$K/run_freemath_local.sh Qwen/Qwen3-8B hardmath2 realmath
$K/run_final_forced.sh Qwen/Qwen3-8B beyondaime hardmath2 realmath
cd $W/SkillOpt && .venv/bin/python $K/rescore_freemath.py $W qwen3-8b
echo "[v4] ALL_DONE"
