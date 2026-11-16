#!/bin/bash
# Queue step 3: GEPA on the T2 split (train 100 / val 150) for MMLU-Pro math, Qwen3-8B on GPU 0 and Qwen3-14B on
# GPU 1, same settings as math_gepa (greedy, budget 1200, reflection LM = the target). Then test greedy on the 255
# T2 test questions: none / seed prompt / GEPA-T2 skill / the old GEPA skill (T1 split). Results: ~/math_gepa/results_t2
set -uo pipefail
cd "$(dirname "$0")"; H=$(pwd)
D=$HOME/math_gepa; W=$HOME/skillopt_work; MQ=$HOME/mcq_math; PY=$W/vllm_env/bin/python; B=mmlupro_math_tq_sb
log() { echo "$(date '+%F %T') $*" | tee -a $H/jobs.txt; }
cp $H/split_t2_ids.json $D/split_t2_ids.json
python3 -c "import json;print(json.dumps(json.load(open('$D/split_t2_ids.json'))['test']))" > $D/ids_test_t2.json
one() {  # <hf model> <gpu> <port>
  local M=$1 G=$2 P=$3 tag; tag=$(basename $M | tr A-Z a-z); local O=$D/gepa_t2/$tag/$B; mkdir -p $O
  if [ ! -s $O/skill.md ]; then
    (cd $D && HF_HUB_OFFLINE=1 bash serve.sh $M $G $P > $O/server.log 2>&1) & local SP=$!
    until curl -sf localhost:$P/v1/models >/dev/null; do sleep 10; kill -0 $SP 2>/dev/null || { log "gepa_t2 server died $tag"; return 1; }; done
    log "gepa_t2 $tag start"
    (cd $D && GEPA_SPLIT_IDS=$D/split_t2_ids.json ~/rg_env/bin/python gepa_math.py --bench $B --model $M --out_dir $O --budget 1200 --port $P > $O.log 2>&1)
    log "gepa_t2 $tag rc=$? $(tail -1 $O.log)"
    kill $SP; wait $SP 2>/dev/null; sleep 10
  fi
  [ -s $O/skill.md ] || { log "GEPA_T2_FAILED $tag"; return 1; }
  mkdir -p $D/skills/$tag; cp $O/skill.md $D/skills/$tag/gepa_t2_$B.md
  CUDA_VISIBLE_DEVICES=$G VLLM_CACHE_ROOT=/dev/shm/$USER-mg$G HF_HUB_OFFLINE=1 PATH=$W/vllm_env/bin:$PATH MODEL_ID=$M \
    $PY $MQ/evaluate_vllm_mcq.py --data $MQ/data/$B.jsonl --ids $D/ids_test_t2.json --tag t2test --out-dir $D/results_t2 \
    --max-new-tokens 2048 --skills none $D/skills/seed_skill.md $D/skills/$tag/gepa_t2_$B.md $D/skills/$tag/gepa_$B.md \
    > $D/results_t2_$tag.log 2>&1
  log "gepa_t2 test $tag rc=$?"
}
mkdir -p $D/results_t2
one Qwen/Qwen3-8B 0 8111 & one Qwen/Qwen3-14B 1 8112 & wait
log "GEPA_T2_DONE"
