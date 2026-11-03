#!/bin/bash
# test_skills.sh <gpu> <hf_model>: GEPA skill + seed skill on every benchmark's test split, with the main-table runners.
# Existing cells (baseline / placebo_notation / brevity_control) are reused from ~/budget/results.
G=$1; M=$2; tag=$(basename $M | tr A-Z a-z)
W=$HOME/skillopt_work; MQ=$HOME/mcq_math; PY=$W/vllm_env/bin/python; D=$HOME/math_gepa
export PATH=$W/vllm_env/bin:$PATH HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
U=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i $G); [ "$U" -gt 2048 ] && { echo "GPU $G busy"; exit 1; }
mkdir -p $D/results $D/skills/$tag
echo "Solve the task step by step and check your work before answering." > $D/skills/seed_skill.md
for b in mmlupro_math_tq_sb supergpqa_math_hard beyondaime hardmath2 realmath imoanswer arxivmath; do
  cp $D/gepa/$tag/$b/skill.md $D/skills/$tag/gepa_$b.md || { echo "no skill for $b"; continue; }
  S="$D/skills/$tag/gepa_$b.md $D/skills/seed_skill.md"
  if [[ $b == mmlupro* || $b == supergpqa* ]]; then
    CUDA_VISIBLE_DEVICES=$G VLLM_CACHE_ROOT=/dev/shm/$USER-mg$G MODEL_ID=$M $PY $MQ/evaluate_vllm_mcq.py --data $MQ/data/$b.jsonl \
      --ids $MQ/protocol/$b/ids_test.json --tag test --out-dir $D/results --max-new-tokens 2048 --skills $S
  else
    CUDA_VISIBLE_DEVICES=$G VLLM_CACHE_ROOT=/dev/shm/$USER-mg$G MODEL_ID=$M $PY $W/kit_v4/freemath/evaluate_vllm_freemath.py \
      --items $W/fm_split/$b/test/items.json --bench $b --tag test --out-dir $D/results --max-new-tokens 2048 --skills $S
  fi
  echo "[test] $b $tag rc=$?"
done
~/rg_env/bin/python $D/rescore_mv.py $D/results $D/results_mv 2>&1 | grep -v "Timeout is disabled"
echo TEST_DONE $tag
