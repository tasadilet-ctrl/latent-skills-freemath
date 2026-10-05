#!/bin/bash
#SBATCH --job-name=ls_hooktest
#SBATCH --output=/shared/home/adil.taibassarov/latent-skills/logs/hooktest_%j.out
#SBATCH -A issai
#SBATCH -p H100
#SBATCH -q issai-h100
#SBATCH --nodes=1
#SBATCH --gpus-per-node=2
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH -t 01:00:00
#SBATCH --exclude=g002,g006
# End-to-end check of src/serve_hooked.py BEFORE any cell is spent on it:
# does it serve, does it emit parseable tool calls, and does steering change
# the output? Steering that silently does nothing would look like a null.
set -uo pipefail
source /shared/home/adil.taibassarov/latent-skills/env.sh
PORT=8077
VEC="${VEC:-vectors/v_qwen3-14b_spreadsheet_edit_spreadsheet_n50_plain.pt}"

run_server() {  # $1 = extra args
  MODEL_ID="${MODEL_ID}" "$LS_PY" "$LS_ROOT/src/serve_hooked.py" \
     --port $PORT --served-name test $1 > "$LS_ROOT/logs/hooktest_${SLURM_JOB_ID}_srv.log" 2>&1 &
  echo $!
}
wait_ready() {
  for i in $(seq 1 120); do
    curl -sf -m 5 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && return 0
    kill -0 "$1" 2>/dev/null || { echo "server died"; tail -20 "$LS_ROOT/logs/hooktest_${SLURM_JOB_ID}_srv.log"; return 1; }
    sleep 10
  done; return 1
}
ask() {
  curl -s -m 300 -w "\n  HTTP:%{http_code}" "http://127.0.0.1:$PORT/v1/chat/completions" -H 'Content-Type: application/json' -d '{
   "model":"test","messages":[{"role":"user","content":"List files in the current directory. Use the tool."}],
   "tools":[{"type":"function","function":{"name":"terminal","parameters":{"type":"object",
     "properties":{"command":{"type":"string"}},"required":["command"]}}}],
   "tool_choice":"auto","max_tokens":300}'
}

echo "### 1. UNSTEERED"
P=$(run_server ""); wait_ready "$P" || exit 1
R=$(ask)
echo "  RAW: ${R:0:500}"
echo "$R" | "$LS_PY" -c "
import json,sys
raw=sys.stdin.read()
try: d=json.loads(raw)
except Exception: raise SystemExit
if 'choices' in d:
    m=d['choices'][0]['message']
    print('  tool_calls:',len(m.get('tool_calls') or []))
    print('  content:',repr((m.get('content') or '')[:150]))
" 2>/dev/null
kill "$P" 2>/dev/null; sleep 20

echo "### 2. STEERED (L38 g0.3)"
P=$(run_server "--vectors $LS_ROOT/$VEC --layers 38 --gamma 0.3"); wait_ready "$P" || exit 1
curl -sf -m 10 "http://127.0.0.1:$PORT/health"; echo
R=$(ask)
echo "  RAW: ${R:0:500}"
echo "$R" | "$LS_PY" -c "
import json,sys
raw=sys.stdin.read()
try: d=json.loads(raw)
except Exception: raise SystemExit
if 'choices' in d:
    m=d['choices'][0]['message']
    print('  tool_calls:',len(m.get('tool_calls') or []))
    print('  content:',repr((m.get('content') or '')[:150]))
" 2>/dev/null
kill "$P" 2>/dev/null
echo "### done"
