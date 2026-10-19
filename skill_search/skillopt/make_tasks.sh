#!/usr/bin/env bash
# Writes the task lists for the SkillOpt LiveMath run (one shell command per line).
# HF transformers cells (comparable with results/ baselines) and vLLM text cells
# (comparable with results_vllm/full baselines). See README.md here.
KIT=$(cd "$(dirname "$0")/../.." && pwd); SK=$KIT/skills/skillopt; V=$KIT/vectors
IDS=$KIT/skill_search/ids_skillopt_trainval.json
: > extract.txt; : > eval_hf.txt; : > eval_vllm.txt
for spec in "Qwen/Qwen3-8B qwen3-8b 34 2048 4" "Qwen/Qwen3.6-27B qwen3.6-27b 62 4096 8"; do
  set -- $spec; M=$1; T=$2; L=$3; MX=$4; K=$5
  X="MODEL_ID=$M python $KIT/src/extract_vectors.py --pool livemath --ids $IDS --n 50"
  echo "$X --skill $SK/skillopt_full.md --baseline-skill $SK/placebo_skillopt_full.md --out $V/v_${T}_skillopt_full_lmtv_n50_placebo.pt" >> extract.txt
  echo "$X --skill $SK/skillopt_full.md --out $V/v_${T}_skillopt_full_lmtv_n50_plain.pt" >> extract.txt
  echo "$X --skill $SK/placebo_skillopt_full.md --out $V/v_${T}_placebo_skillopt_full_lmtv_n50_plain.pt" >> extract.txt
  E="MODEL_ID=$M python $KIT/src/evaluate.py --domain livemath --limit 608 --batch-size 8 --max-new-tokens $MX"
  for i in $(seq 0 $((K-1))); do
    echo "$E --condition text --skill $SK/skillopt_full.md --shard $i/$K" >> eval_hf.txt
    for v in skillopt_full_lmtv_n50_placebo skillopt_full_lmtv_n50_plain placebo_skillopt_full_lmtv_n50_plain; do
      echo "$E --condition embed --vectors $V/v_${T}_$v.pt --layers $L --gamma 0.3 --mode relative --shard $i/$K" >> eval_hf.txt
    done
  done
done
for spec in "Qwen/Qwen3-8B 2048" "Qwen/Qwen3-14B 2048" "Qwen/Qwen3.6-27B 4096"; do
  set -- $spec
  for g in 0 1 2 3; do
    echo "MODEL_ID=$1 python $KIT/src/evaluate_vllm.py --skills $SK/skillopt_full.md $SK/skillopt_nometa.md $SK/placebo_skillopt_full.md $SK/placebo_skillopt_nometa.md --max-new-tokens $2 --shard $g/4 --out-dir $KIT/results_vllm/skillopt" >> eval_vllm.txt
  done
done
wc -l extract.txt eval_hf.txt eval_vllm.txt
