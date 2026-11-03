#!/bin/bash
# run_gepa.sh <gpu> <hf_model> [budget] [port]: one GEPA skill per math-suite benchmark, all 7 in parallel on one server
G=$1; M=$2; B=${3:-1200}; P=${4:-8100}
cd ~/math_gepa; tag=$(basename $M | tr A-Z a-z); mkdir -p gepa/$tag
export HF_HUB_OFFLINE=1
bash serve.sh $M $G $P > gepa/$tag/server.log 2>&1 & SP=$!
until curl -sf localhost:$P/v1/models >/dev/null; do sleep 10; kill -0 $SP 2>/dev/null || { echo "server died"; exit 1; }; done
one() { T=$1
  [ -s gepa/$tag/$T/skill.md ] && { echo "skip $T"; return; }
  ~/rg_env/bin/python gepa_math.py --bench $T --model $M --out_dir gepa/$tag/$T --budget $B --port $P > gepa/$tag/$T.log 2>&1 \
    && tail -1 gepa/$tag/$T.log || echo "FAILED $T"; }
export -f one; export tag B P M
echo mmlupro_math_tq_sb supergpqa_math_hard beyondaime hardmath2 realmath imoanswer arxivmath | tr ' ' '\n' | xargs -P 7 -I{} bash -c 'one {}'
kill $SP; wait $SP 2>/dev/null
echo GEPA_DONE $tag
