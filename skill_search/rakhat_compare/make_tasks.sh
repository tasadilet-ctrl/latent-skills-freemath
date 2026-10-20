#!/usr/bin/env bash
# LiveMath: our vectors vs Rakhat's (rakhat/step-vector-pilot), skill livemath_ts.
#   prep.txt    4B replies (vLLM), 4B kit vectors, Rakhat vectors for 14B/27B,
#               and every HF cell that needs nothing new
#   prep4b.txt  Rakhat vectors for 4B (needs the 4B replies)
#   rakhat.txt  Rakhat's four vectors as HF cells
# Operating points. Ours: single layer, gamma 0.3 relative (4B L34 as in Rakhat's
# kit cells, 14B L37, 27B L62, as in every earlier LiveMath table). Rakhat's reply
# vectors: the second half of the layers, gamma 0.02 relative (his 4B L18-35 g0.02,
# scaled by depth). Step vectors: his 4B layer 32 of 36, scaled by depth; strength 1.5.
K=/shared/home/adil.taibassarov/latent-skills-kit
S=$K/skills; V=$K/vectors
EV="python $K/src/evaluate.py --domain livemath --limit 0 --batch-size 8"
: > prep.txt; : > prep4b.txt; : > rakhat.txt
#        model            tag          ours  reply   step tokens shards
for spec in "Qwen/Qwen3-4B qwen3-4b 34 18-35 32 2048 2" \
            "Qwen/Qwen3-14B qwen3-14b 37 20-39 36 2048 2" \
            "Qwen/Qwen3.6-27B qwen3.6-27b 62 32-63 57 4096 4"; do
  set -- $spec; M=$1; T=$2; L=$3; RL=$4; SL=$5; TOK=$6; SH=$7
  E="MODEL_ID=$M $EV --max-new-tokens $TOK"
  if [ $T = qwen3-4b ]; then
    echo "MODEL_ID=$M python $K/src/evaluate_vllm.py --skills $S/livemath_ts.md $S/placebo_livemath_ts.md --max-new-tokens 2048 --shard 0/1 --out-dir $K/results_vllm/ts" >> prep.txt
    echo "MODEL_ID=$M python $K/src/extract_vectors.py --pool neutral --n 50 --skill $S/livemath_ts.md --baseline-skill $S/placebo_livemath_ts.md --out $V/v_${T}_livemath_ts_neutral_n50_placebo.pt" >> prep.txt
    echo "MODEL_ID=$M python $K/src/extract_vectors.py --pool neutral --n 50 --skill $S/livemath_ts.md --out $V/v_${T}_livemath_ts_neutral_n50_plain.pt" >> prep.txt
    echo "MODEL_ID=$M python $K/src/rakhat_vectors.py --skill $S/livemath_ts.md" >> prep4b.txt
  else
    echo "MODEL_ID=$M python $K/src/rakhat_vectors.py --skill $S/livemath_ts.md" >> prep.txt
  fi
  for ((i=0; i<SH; i++)); do
    [ $T = qwen3-4b ] && echo "$E --condition baseline --shard $i/$SH" >> prep.txt
    echo "$E --condition text --skill $S/livemath_ts.md --shard $i/$SH" >> prep.txt
    for side in placebo plain; do
      f="$E --condition embed --vectors $V/v_${T}_livemath_ts_neutral_n50_${side}.pt --layers $L --gamma 0.3 --mode relative --shard $i/$SH"
      if [ $T = qwen3-4b ]; then echo "$f" >> rakhat.txt; else echo "$f" >> prep.txt; fi
    done
    for side in A B; do
      echo "$E --condition embed --vectors $V/v_${T}_livemath_ts_reply${side}.pt --layers $RL --gamma 0.02 --mode relative --shard $i/$SH" >> rakhat.txt
      echo "$E --condition step --vectors $V/v_${T}_livemath_ts_step${side}.pt --layers $SL --strength 1.5 --shard $i/$SH" >> rakhat.txt
    done
  done
done
wc -l prep.txt prep4b.txt rakhat.txt
