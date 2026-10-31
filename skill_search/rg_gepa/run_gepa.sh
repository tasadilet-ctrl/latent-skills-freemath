#!/bin/bash
# run_gepa.sh <gpu> <hf_model> <budget> <task1,task2,...>: one GEPA skill per task (6 tasks in parallel on one server)
G=$1; M=$2; B=$3; TASKS=$4; P=${PORT:-8100}; J=${JOBS:-6}
cd ~/rg_gepa; tag=$(basename $M | tr A-Z a-z); mkdir -p gepa/$tag
bash serve.sh $M $G $P > gepa/$tag/server.log 2>&1 & SP=$!
until curl -sf localhost:$P/v1/models >/dev/null; do sleep 10; kill -0 $SP 2>/dev/null || { echo "server died"; exit 1; }; done
one() { T=$1
  [ -s gepa/$tag/$T/skill.md ] && { echo "skip $T"; return; }
  ~/rg_env/bin/python gepa_skill.py --task $T --out_dir gepa/$tag/$T --budget $B --port $P > gepa/$tag/$T.log 2>&1 \
    && tail -1 gepa/$tag/$T.log || echo "FAILED $T"; }
export -f one; export tag B P
echo ${TASKS//,/ } | tr ' ' '\n' | xargs -P $J -I{} bash -c 'one {}'
kill $SP; wait $SP 2>/dev/null
echo GEPA_DONE $tag
