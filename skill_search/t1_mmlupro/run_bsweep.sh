#!/bin/bash
# Batch-size sweep for SkillOpt on the Reasoning Gym control (Qwen3-14B, decimal_arithmetic: first SkillOpt run
# 37-40, so there is room). Train 100 questions (seed 11), val 40 x 4 (seed 12). Batch in 100 50 20 10 1,
# 4 epochs each (= 400 training examples seen, 4 to 40 steps), except batch 1: 1 epoch (100 steps) to keep it
# under a day. Test as run_rg.sh: fresh seed 100000, n 200, greedy + T 1.0 seeds 1-3.
# Results: ~/rg_gepa/skillopt_ctrl/bsweep/decimal_arithmetic_b<B>_<mode>.jsonl, skills in .../bsweep/skills/
set -uo pipefail
cd "$(dirname "$0")"; H=$(pwd)
W=$HOME/skillopt_work; RG=$HOME/rg_gepa; T=decimal_arithmetic; S=14b
SPL=$W/rg_split_n100; D=$RG/skillopt_ctrl/bsweep; mkdir -p $D/skills
log() { echo "$(date '+%F %T') $*" | tee -a $H/jobs.txt; }
[ -s $SPL/$T/train/items.json ] || RG_TRAIN_N=100 ~/rg_env/bin/python make_rg_split.py $SPL $T >> logs_rg_setup.log 2>&1 \
  || { log "BSWEEP split failed"; exit 1; }
for B in 100 50 20 10 1; do
  E=4; [ $B = 1 ] && E=1
  out=$W/outputs/rg_${T}_${S}_b${B}
  if [ ! -s $out/summary.json ]; then
    log "bsweep train b$B e$E start"
    RUN_NAME=rg_${T}_${S}_b${B} RG_SPLIT=$SPL BATCH=$B EPOCHS=$E bash train_rg.sh $S $T >> train_driver.log 2>&1
    log "bsweep train b$B rc=$?"
  fi
  [ -s $out/best_skill.md ] && grep -v "SLOW_UPDATE_\(START\|END\)" $out/best_skill.md > $D/skills/b${B}.md
done
P=8103
(cd $RG && HF_HUB_OFFLINE=1 setsid bash serve.sh Qwen/Qwen3-14B 0 $P > $D/server.log 2>&1) & SP=$!
until curl -sf localhost:$P/v1/models >/dev/null; do sleep 10; kill -0 $SP 2>/dev/null || { log "bsweep test server died"; exit 1; }; done
for f in $D/skills/b*.md; do
  b=$(basename $f .md)
  for mode in t0 t1s1 t1s2 t1s3; do
    o=$D/${T}_${b}_${mode}.jsonl; [ -s $o ] && continue
    case $mode in t0) TS="--temperature 0";; t1s*) TS="--temperature 1.0 --req-seed ${mode#t1s}";; esac
    ~/rg_env/bin/python $H/rg_eval_t.py --tasks $T --n 200 --seed 100000 --skill $f $TS --port $P --out $o > ${o%.jsonl}.txt 2>&1
    log "bsweep test $b $mode: $(grep -o 'acc= *[0-9.]*' ${o%.jsonl}.txt)"
  done
done
PG=$(pgrep -u "$USER" -P $SP | head -1)
[ -n "$PG" ] && kill -- -$PG 2>/dev/null; kill $SP 2>/dev/null; wait $SP 2>/dev/null
log "BSWEEP_DONE"
