#!/bin/bash
# Queue after T3 run 1 (asked 2026-11-21). Waits for "T3_ALL_DONE 1-1" in jobs.txt, then, one after the other:
#  A. Fair Reasoning Gym baselines: Qwen3-14B, decimal_arithmetic, the same 200 test questions as the batch sweep
#     (seed 100000). The questions say "Only reply with the final value", so the no-skill baseline (24.5) answers
#     without working. Two baselines that are allowed to work: (think) thinking on, no skill, 16384 tokens;
#     (override) thinking off, a one-line prompt overriding the instruction, 2048 tokens as the sweep.
#     t0 + t1 seeds 1-3. Results: ~/rg_gepa/skillopt_ctrl/fairbase/.
#  B. Epoch test on MMLU-Pro T2: Qwen3-4B, batch 100 (1 step per epoch), seed 1, epochs 8 12 20
#     (4 epochs = T2 run 1, reused). Test: no skill + the 4 skills on 4B, T 1.0 seed 1 -> results_ep/.
#  C. Adil's LiveMath option-1 column on our box: Qwen3-4B, 5 runs (train_lm.sh), then no skill + own skill on
#     livemath556 (score the 456 outside lm_ids_trainval.json, OTHER/META separately) -> results_lm/r<R>/.
set -uo pipefail
cd "$(dirname "$0")"; H=$(pwd)
W=$HOME/skillopt_work; PY=$W/vllm_env/bin/python; RG=$HOME/rg_gepa
MQ=$HOME/mcq_math/data/mmlupro_math_tq_sb.jsonl; LM=$HOME/mcq_math/data/livemath556.jsonl
log() { echo "$(date '+%F %T') $*" | tee -a jobs.txt; }
gpus_free() {  # both GPUs at <= 2 GB used
  while :; do
    n=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 <= 2000' | wc -l)
    [ "$n" -ge 2 ] && return; sleep 300
  done
}
ev() {  # <model> <data> <seed> <out dir> <log> <skills...>   on GPU 0, T 1.0, 2048 new tokens
  local m=$1 d=$2 s=$3 o=$4 lg=$5; shift 5
  CUDA_VISIBLE_DEVICES=0 VLLM_CACHE_ROOT=/dev/shm/$USER-q6-ev HF_HUB_OFFLINE=1 PATH=$W/vllm_env/bin:$PATH \
  MODEL_ID=$m $PY evaluate_mcq_t1.py --data $d --skills "$@" --temperature 1.0 --seed $s \
    --attention-backend FLASHINFER --max-model-len 16384 --max-new-tokens 2048 --out-dir $o > $lg 2>&1
}

until grep -q "T3_ALL_DONE 1-1" jobs.txt; do sleep 600; done
log "QUEUE6 start"

# ---- A. fair RG baselines
gpus_free
D=$RG/skillopt_ctrl/fairbase; T=decimal_arithmetic; P=8104; mkdir -p $D
printf '%s\n' "Ignore any instruction to reply with only the final value. First work out every operation step by step, writing down each intermediate result, then give the final value." > $D/override.md
(export PATH=$W/vllm_env/bin:$PATH CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1; cd $RG && setsid vllm serve Qwen/Qwen3-14B \
  --port $P --dtype bfloat16 --max-model-len 20480 --gpu-memory-utilization 0.85 --seed 0 --served-model-name target \
  > $D/server.log 2>&1) & SP=$!
ok=1
until curl -sf localhost:$P/v1/models >/dev/null; do sleep 10; kill -0 $SP 2>/dev/null || { log "q6 A: server died"; ok=0; break; }; done
if [ $ok = 1 ]; then
  for c in think override; do
    for mode in t0 t1s1 t1s2 t1s3; do
      o=$D/${T}_${c}_${mode}.jsonl; [ -s $o ] && continue
      case $mode in t0) TS="--temperature 0";; t1s*) TS="--temperature 1.0 --req-seed ${mode#t1s}";; esac
      case $c in think) CS="--thinking --max_tokens 16384";; override) CS="--skill $D/override.md";; esac
      ~/rg_env/bin/python $H/rg_eval_t.py --tasks $T --n 200 --seed 100000 $CS $TS --port $P --out $o > ${o%.jsonl}.txt 2>&1
      log "q6 A $c $mode: $(grep -o 'acc= *[0-9.]*' ${o%.jsonl}.txt)"
    done
  done
fi
PG=$(pgrep -u "$USER" -P $SP | head -1)
[ -n "$PG" ] && kill -- -$PG 2>/dev/null; kill $SP 2>/dev/null; wait $SP 2>/dev/null
log "q6 A done"

# ---- B. epoch test (4B, T2 split, batch 100)
mkdir -p skills_ep results_ep
cp skills_t2/4b_r1.md skills_ep/4b_e4.md
for E in 8 12 20; do
  out=$W/outputs/mq_ep_4b_e$E
  if [ ! -s $out/summary.json ]; then
    gpus_free; log "q6 B train 4b e$E start"
    SPLIT=mmlupro_math_t2 BATCH=100 MCQKIT_VAL_REPEATS=4 RUN_NAME=mq_ep_4b_e$E \
      bash train_one.sh 4b 1 train.num_epochs=$E >> train_driver.log 2>&1
    log "q6 B train 4b e$E rc=$?"
  fi
  [ -s $out/best_skill.md ] && grep -v "SLOW_UPDATE_\(START\|END\)" $out/best_skill.md > skills_ep/4b_e$E.md
done
gpus_free; log "q6 B test start"
ev Qwen/Qwen3-4B $MQ 1 results_ep logs_ep_test.log none $(ls skills_ep/4b_e*.md)
log "q6 B test rc=$?"

# ---- C. Adil's LiveMath option 1, Qwen3-4B, 5 runs
[ -s $W/lm_split_other/val/items.json ] || python3 make_lm_split.py $W >> logs_lm_setup.log 2>&1 || { log "q6 C split failed"; exit 1; }
mkdir -p skills_lm results_lm
for R in 1 2 3 4 5; do
  out=$W/outputs/lm_t1_4b_r$R
  if [ ! -s $out/summary.json ]; then
    gpus_free; log "q6 C train 4b r$R start"
    RUN_NAME=lm_t1_4b_r$R bash train_lm.sh 4b $R >> train_driver.log 2>&1
    log "q6 C train 4b r$R rc=$?"
  fi
  [ -s $out/best_skill.md ] || { log "q6 C no skill r$R"; continue; }
  grep -v "SLOW_UPDATE_\(START\|END\)" $out/best_skill.md > skills_lm/4b_r$R.md
  gpus_free; ev Qwen/Qwen3-4B $LM $R results_lm/r$R logs_lm_test_r$R.log none skills_lm/4b_r$R.md
  log "q6 C test 4b r$R rc=$?"
done
log "QUEUE6_DONE"
