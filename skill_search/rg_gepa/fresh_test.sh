#!/bin/bash
# fresh_test.sh <gpu>: random-vector control (HF), then GEPA test on a fresh seed (100000, items never used) with vLLM
G=$1; cd ~/rg_gepa; P=8100
export KIT=$HOME/vec_arm/kit HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1
PY="$HOME/for Adilet/.venv/bin/python"
(cd vec && "$PY" ~/rg_gepa/mkrand.py)
for MB in Qwen/Qwen3-14B:decimal_arithmetic:32 Qwen/Qwen3-8B:products:48; do
  IFS=: read M B BS <<< "$MB"
  for s in 1 2; do (cd vec && CUDA_VISIBLE_DEVICES=$G MODEL_ID=$M "$PY" vec_rg.py eval --bench $B --cond B1 --max-new-tokens 2048 --batch-size $BS --out-dir rand$s 2>&1 | grep "\[vec\] {"); done
done
mkdir -p fresh
for MT in Qwen/Qwen3-8B:products,word_sorting Qwen/Qwen3-14B:products,decimal_arithmetic; do
  M=${MT%%:*}; TS=${MT##*:}; tag=$(basename $M | tr A-Z a-z); mkdir -p fresh/$tag
  bash serve.sh $M $G $P > fresh/$tag/server.log 2>&1 & SP=$!
  until curl -sf localhost:$P/v1/models >/dev/null; do sleep 10; kill -0 $SP 2>/dev/null || { echo "server died"; exit 1; }; done
  for c in none seed placebo brevity; do
    SK=""; case $c in seed) SK="--skill seed_skill.md";; placebo) SK="--skill placebo_notation.md";; brevity) SK="--skill brevity_control.md";; esac
    ~/rg_env/bin/python rg_eval.py --tasks $TS --n 200 --seed 100000 $SK --port $P --out fresh/$tag/default_$c.jsonl > fresh/$tag/default_$c.txt 2>&1
  done
  for t in ${TS//,/ }; do ~/rg_env/bin/python rg_eval.py --tasks $t --n 200 --seed 100000 --skill gepa/$tag/$t/skill.md --port $P --out fresh/$tag/default_gepa_$t.jsonl > /dev/null 2>&1; done
  cat fresh/$tag/default_gepa_*.jsonl > fresh/$tag/default_gepa.jsonl
  kill $SP; wait $SP 2>/dev/null; sleep 5
done
echo FRESH_DONE
