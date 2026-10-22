#!/usr/bin/env bash
# PROTOCOL.md stage for the mcqmath SkillOpt runs: SkillOpt's accepted skills (+ seed) are the drafts;
# dev selection over Qwen3-8B / Qwen3-14B / Qwen3.6-27B; then the test split, once, on all three.
# Same stack for every cell: evaluate_vllm_mcq.py (kit prompt + answer forcing), greedy, thinking off,
# 2048 new tokens (4096 for the 27B), as PROTOCOL.md's final report specifies.
#   ./run_protocol_mq.sh [benches...]     default: mmlupro_math_tq_sb supergpqa_math_hard
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE"
W=$HOME/skillopt_work; PY=$W/vllm_env/bin/python
export PATH=$W/vllm_env/bin:$PATH HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES=${GPU:-1} VLLM_CACHE_ROOT=/dev/shm/$USER-proto0
BENCHES=${*:-mmlupro_math_tq_sb supergpqa_math_hard}
declare -A TOK=([Qwen/Qwen3-8B]=2048 [Qwen/Qwen3-14B]=2048 [Qwen/Qwen3.6-27B]=4096)
MODELS=(Qwen/Qwen3.6-27B Qwen/Qwen3-14B Qwen/Qwen3-8B)   # reverse order: shares the work with the GPU-1 chain
for b in $BENCHES; do
  P=$HERE/protocol/$b; mkdir -p $P/drafts $P/results
  SO=$W/outputs/mq_${b}_qwen3-8b
  [ -f $SO/summary.json ] || { echo "[proto] $b: SkillOpt run not finished, skipping"; continue; }
  # drafts = distinct skill texts SkillOpt produced (seed + accepted versions + best)
  for f in $SO/skills/skill_v*.md $SO/best_skill.md; do
    h=$(md5sum < "$f" | cut -c1-8); [ -n "$(ls $P/drafts/*_$h.md 2>/dev/null)" ] && continue
    cp "$f" "$P/drafts/$(basename "$f" .md)_$h.md"
  done
  for s in val test; do
    python3 -c "import json,sys; json.dump([it['id'] for it in json.load(open(sys.argv[1]))], open(sys.argv[2],'w'))" \
      $W/mq_split/$b/$s/items.json $P/ids_$s.json
  done
  echo "[proto] $b drafts: $(ls $P/drafts | tr '\n' ' ')"
  for m in "${MODELS[@]}"; do
    MODEL_ID=$m $PY evaluate_vllm_mcq.py --data data/$b.jsonl --ids $P/ids_val.json --tag dev \
      --out-dir $P/results --max-new-tokens ${TOK[$m]} --skills none $P/drafts/*.md
    echo "[proto] $b dev $m rc=$?"
  done
  python3 protocol_select.py select $P/results $b $P/drafts $P/chosen.md | tee $P/selection.txt
  [ -f $P/chosen.md ] || { echo "[proto] $b: no chosen draft"; continue; }
  for m in "${MODELS[@]}"; do
    MODEL_ID=$m $PY evaluate_vllm_mcq.py --data data/$b.jsonl --ids $P/ids_test.json --tag test \
      --out-dir $P/results --max-new-tokens ${TOK[$m]} \
      --skills none skills/placebo_matched.md skills/strength_audit.md skills/strength_audit_nometa.md \
               skills/placebo_livemath_ts.md skills/livemath_ts.md $P/chosen.md
    echo "[proto] $b test $m rc=$?"
  done
  python3 protocol_select.py report $P/results $b | tee $P/report.txt
done
echo "[proto] ALL_DONE"
