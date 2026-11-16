#!/bin/bash
# Queue step 2: SkillOpt positive control on Reasoning Gym (Qwen3-8B products, Qwen3-14B decimal_arithmetic,
# the GEPA control's two strongest cells). Install the rgym env, build the split, train both, then test on the
# fresh seed 100000 (n 200): none / seed prompt / SkillOpt skill / GEPA skill, greedy and T 1.0 (seeds 1-3).
# Results: ~/rg_gepa/skillopt_ctrl/<model tag>/<task>_<condition>_<t0|t1s1|t1s2|t1s3>.jsonl
set -uo pipefail
cd "$(dirname "$0")"; H=$(pwd)
W=$HOME/skillopt_work; RG=$HOME/rg_gepa
log() { echo "$(date '+%F %T') $*" | tee -a $H/jobs.txt; }
# reasoning_gym in SkillOpt's venv (same version as ~/rg_env)
if ! $W/SkillOpt/.venv/bin/python -c "import reasoning_gym" 2>/dev/null; then
  UV=$(ls $W/uvenv/bin/uv ~/.local/bin/uv ~/.cargo/bin/uv 2>/dev/null | head -1)
  if [ -n "$UV" ]; then $UV pip install --python $W/SkillOpt/.venv/bin/python reasoning_gym==0.1.19 >> logs_rg_setup.log 2>&1
  else ~/rg_env/bin/python -m pip download reasoning_gym==0.1.19 --no-deps -d /tmp/$USER-rgwheel >> logs_rg_setup.log 2>&1
       $W/SkillOpt/.venv/bin/python -m ensurepip >> logs_rg_setup.log 2>&1
       $W/SkillOpt/.venv/bin/python -m pip install reasoning_gym==0.1.19 >> logs_rg_setup.log 2>&1; fi
fi
$W/SkillOpt/.venv/bin/python -c "import reasoning_gym" || { log "RG_SETUP_FAILED (reasoning_gym not importable)"; exit 1; }
python3 patch_rgym.py $W/SkillOpt rgym_env >> logs_rg_setup.log 2>&1 || { log "RG_SETUP_FAILED (patch)"; exit 1; }
~/rg_env/bin/python make_rg_split.py $W/rg_split products decimal_arithmetic >> logs_rg_setup.log 2>&1 || { log "RG_SETUP_FAILED (split)"; exit 1; }
log "rg setup ok"
for ST in 8b:products 14b:decimal_arithmetic; do
  s=${ST%%:*}; t=${ST##*:}; out=$W/outputs/rg_${t}_${s}_r1
  if [ ! -s $out/summary.json ]; then
    log "rg train $s $t start"; bash train_rg.sh $s $t >> train_driver.log 2>&1; log "rg train $s $t rc=$?"
  fi
  [ -s $out/best_skill.md ] || { log "RG_TRAIN_FAILED $s $t"; exit 1; }
  mkdir -p $RG/skillopt_ctrl/skills
  grep -v "SLOW_UPDATE_\(START\|END\)" $out/best_skill.md > $RG/skillopt_ctrl/skills/skillopt_${s}_${t}.md
done
test_model() {  # <size> <task> <gpu> <port>
  declare -A HFM=([8b]=Qwen/Qwen3-8B [14b]=Qwen/Qwen3-14B)
  local s=$1 t=$2 g=$3 P=$4 M tag; M=${HFM[$s]}
  tag=$(basename $M | tr A-Z a-z); local D=$RG/skillopt_ctrl/$tag; mkdir -p $D
  (cd $RG && HF_HUB_OFFLINE=1 bash serve.sh $M $g $P > $D/server.log 2>&1) & local SP=$!
  until curl -sf localhost:$P/v1/models >/dev/null; do sleep 10; kill -0 $SP 2>/dev/null || { log "rg test server died $s"; return 1; }; done
  declare -A SK=([none]="" [seed]="--skill $RG/seed_skill.md" [skillopt]="--skill $RG/skillopt_ctrl/skills/skillopt_${s}_${t}.md" [gepa]="--skill $RG/gepa/$tag/$t/skill.md")
  for c in none seed skillopt gepa; do
    for mode in t0 t1s1 t1s2 t1s3; do
      o=$D/${t}_${c}_${mode}.jsonl; [ -s $o ] && continue
      case $mode in t0) TS="--temperature 0";; t1s*) TS="--temperature 1.0 --req-seed ${mode#t1s}";; esac
      ~/rg_env/bin/python $H/rg_eval_t.py --tasks $t --n 200 --seed 100000 ${SK[$c]} $TS --port $P --out $o > ${o%.jsonl}.txt 2>&1
      log "rg test $s $t $c $mode: $(grep -o 'acc= *[0-9.]*' ${o%.jsonl}.txt)"
    done
  done
  kill $SP; wait $SP 2>/dev/null
}
test_model 8b products 0 8101 & test_model 14b decimal_arithmetic 1 8102 & wait
log "RG_DONE"
