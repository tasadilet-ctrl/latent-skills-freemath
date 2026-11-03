#!/bin/bash
# After the GEPA chain: test the SkillOpt drafts that dev selection picks once dev is scored with
# Math-Verify (hardmath2 skill_v0002_61d4bbd9, realmath skill_v0001_06ba8e79, imoanswer best_skill_569fafce),
# 3 models, main-table runner, then rescore with Math-Verify.
cd ~/math_gepa
until grep -q CHAIN_DONE chain.log; do sleep 300; done
W=$HOME/skillopt_work; PY=$W/vllm_env/bin/python; P=$W/protocol_fm
export PATH=$W/vllm_env/bin:$PATH HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
pick() { while true; do
  while IFS=, read -r i u; do [ "${u// /}" -le 2000 ] && { G=${i// /}; return; }; done < <(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits)
  sleep 300; done; }
declare -A TOK=([Qwen/Qwen3-8B]=2048 [Qwen/Qwen3-14B]=2048 [Qwen/Qwen3.6-27B]=4096)
for m in Qwen/Qwen3-8B Qwen/Qwen3-14B Qwen/Qwen3.6-27B; do
  for bd in hardmath2:skill_v0002_61d4bbd9 realmath:skill_v0001_06ba8e79 imoanswer:best_skill_569fafce; do
    b=${bd%%:*}; d=${bd#*:}; pick
    CUDA_VISIBLE_DEVICES=$G VLLM_CACHE_ROOT=/dev/shm/$USER-rs$G MODEL_ID=$m $PY $W/kit_v4/freemath/evaluate_vllm_freemath.py \
      --items $W/fm_split/$b/test/items.json --bench $b --tag test --out-dir $P/$b/results \
      --max-new-tokens ${TOK[$m]} --skills $P/$b/drafts/$d.md
    echo "[reselect] $b $m rc=$?"
    ~/rg_env/bin/python rescore_mv.py $P/$b/results $P/$b/results_mv "${b}_*_${d}_test.json"
  done
done
echo RESELECT_DONE
