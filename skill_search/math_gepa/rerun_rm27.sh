#!/bin/bash
cd ~/math_gepa
W=$HOME/skillopt_work; PY=$W/vllm_env/bin/python; P=$W/protocol_fm; b=realmath; d=skill_v0001_06ba8e79
export PATH=$W/vllm_env/bin:$PATH HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
CUDA_VISIBLE_DEVICES=0 VLLM_CACHE_ROOT=/dev/shm/$USER-rs0 MODEL_ID=Qwen/Qwen3.6-27B $PY $W/kit_v4/freemath/evaluate_vllm_freemath.py \
  --items $W/fm_split/$b/test/items.json --bench $b --tag test --out-dir $P/$b/results \
  --max-new-tokens 4096 --skills $P/$b/drafts/$d.md
echo "[rerun] rc=$?"
~/rg_env/bin/python rescore_mv.py $P/$b/results $P/$b/results_mv "${b}_*_${d}_test.json"
echo RERUN_DONE
