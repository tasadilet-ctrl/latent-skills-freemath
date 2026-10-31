#!/bin/bash
# test_skills.sh <gpu> <hf_model>: test seed 0, n=200, default and hard, 5 conditions (run once)
G=$1; M=$2; P=${PORT:-8100}; cd ~/rg_gepa; tag=$(basename $M | tr A-Z a-z); O=test/$tag; mkdir -p $O
TASKS=$(ls -d gepa/$tag/*/ | xargs -n1 basename | while read t; do [ -s gepa/$tag/$t/skill.md ] && echo $t; done | paste -sd,)
echo "tasks: $TASKS"
bash serve.sh $M $G $P > $O/server.log 2>&1 & SP=$!
until curl -sf localhost:$P/v1/models >/dev/null; do sleep 10; kill -0 $SP 2>/dev/null || { echo "server died"; exit 1; }; done
for split in default hard; do
  CFG=""; [ $split = hard ] && CFG="--config hard_configs.json"
  for c in none seed placebo brevity; do
    SK=""; case $c in seed) SK="--skill seed_skill.md";; placebo) SK="--skill placebo_notation.md";; brevity) SK="--skill brevity_control.md";; esac
    ~/rg_env/bin/python rg_eval.py --tasks $TASKS --n 200 --seed 0 $SK $CFG --port $P --out $O/${split}_$c.jsonl > $O/${split}_$c.txt 2>&1
  done
  for t in ${TASKS//,/ }; do
    ~/rg_env/bin/python rg_eval.py --tasks $t --n 200 --seed 0 --skill gepa/$tag/$t/skill.md $CFG --port $P --out $O/${split}_gepa_$t.jsonl > $O/${split}_gepa_$t.txt 2>&1
  done
  cat $O/${split}_gepa_*.jsonl > $O/${split}_gepa.jsonl
done
kill $SP; wait $SP 2>/dev/null; echo TEST_DONE $tag
