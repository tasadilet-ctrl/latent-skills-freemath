#!/usr/bin/env bash
# lib/common.sh -- shared helpers. Sourced by every run_*.sh.
#
# The one idea here: a cell script says WHAT to run, never WHERE. `submit`
# takes a python command line and either sbatch-es it or runs it locally,
# depending on $RUNNER. That is why the same script works on the cluster and
# on a workstation, and why adding a benchmark does not mean writing two
# launchers.

set -uo pipefail

KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../env.sh
source "$KIT/env.sh"

say()  { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
note() { printf '    %s\n' "$*"; }
warn() { printf '\033[1;33m    ! %s\033[0m\n' "$*"; }
fail() { printf '\n\033[1;31mFAILED: %s\033[0m\n' "$*" >&2; exit 1; }

# Refuse to run before setup.sh has been run -- otherwise the first failure is
# an ImportError three screens down and it is not obvious why.
require_env() {
  local py="$1" what="$2"
  [ -x "$py" ] || fail "no $what environment at $py
    Run ./setup.sh first (or set PY_EVAL / PY_AGENT / PY_PLOT by hand)."
}

require_data() {
  [ -e "$1" ] || fail "missing data: $1
    Run ./setup.sh, or 00_setup/02_benchmark_data.sh on its own."
}

# Is a model being served where the agent harness expects one?
require_served_model() {
  curl -fsS --max-time 5 "${LLM_BASE_URL%/}/health" >/dev/null 2>&1 \
    || curl -fsS --max-time 5 "${LLM_BASE_URL%/v1}/v1/models" >/dev/null 2>&1 \
    || fail "nothing answering at $LLM_BASE_URL
    The agent benchmarks talk to a served model over HTTP; they do not load
    weights themselves. Start one with 00_setup/05_serve_model.sh, or point
    LLM_BASE_URL at an endpoint you already have."
}

# The agent benchmarks get steering from the SERVER, not from a flag: the
# adapters probe /health and label the cell "embed" if it reports a vector.
# So an embed script pointed at a PLAIN server does not fail -- it quietly runs
# and writes a second baseline. Refuse that.
#
#   require_steering [expected-vector-basename]
#
require_steering() {
  local want="${1:-}" health desc
  health="$(curl -fsS --max-time 10 "${LLM_BASE_URL%/v1}/health" 2>/dev/null)" \
    || fail "no /health at ${LLM_BASE_URL%/v1}
    An embed cell needs the HOOKED server (src/serve_hooked.py), not vLLM --
    vLLM exposes no residual stream and cannot steer. Start one:
      00_setup/05_serve_model.sh steered <vectors.pt> <layers> <gamma>"
  desc="$(printf '%s' "$health" | sed -n 's/.*"steering"[ ]*:[ ]*"\([^"]*\)".*/\1/p')"
  case "$desc" in
    ""|none)
      fail "the server at $LLM_BASE_URL is NOT steering.

    It answered /health with steering=\"${desc:-none}\". Running this cell
    against it would produce a second BASELINE, not an embed cell -- the
    adapters label the condition from what the server reports.

    Start the hooked server instead:
      00_setup/05_serve_model.sh steered <vectors.pt> <layers> <gamma>" ;;
  esac
  note "server is steering: $desc"
  if [ -n "$want" ] && [ "${desc#"$want"}" = "$desc" ]; then
    warn "server is steering with '$desc' but this cell names '$want'."
    warn "The result will record what the SERVER used, not what you passed."
  fi
}

# ---------------------------------------------------------------------------
# submit <job-name> <python-interpreter> <script.py> [args...]
#
# RUNNER=sbatch  one SLURM job, $SHARDS shards in parallel, one per GPU
# RUNNER=local   the same shards as background processes across $GPU
#
# Shards are independent: each takes every Nth item and writes its own result
# file; report.py merges them. Sharding across GPUs is ~4x faster than one
# model spread over four.
#
# NO_SHARD=1 omits the --shard argument. The benchmark runners take --shard;
# the vector-pipeline scripts (extract_vectors, fidelity, calibrate,
# compliance_check) do NOT, and argparse rejects the unknown flag instantly --
# the job dies in 9 seconds with "unrecognized arguments: --shard 0/1" after
# waiting however long in the queue. Set it for anything that is not a
# sharded benchmark run.
# ---------------------------------------------------------------------------
submit() {
  local name="$1" py="$2" script="$3"; shift 3
  local args=("$@")
  local shard_flag=1
  [ -n "${NO_SHARD:-}" ] && shard_flag=0

  if [ "$RUNNER" = "sbatch" ]; then
    local sb; sb="$(mktemp "${TMPDIR:-/tmp}/${name}.XXXXXX.sbatch")"
    {
      echo "#!/bin/bash"
      echo "#SBATCH --job-name=ls_${name}"
      echo "#SBATCH --output=$LOGS/${name}_%j.out"
      echo "#SBATCH -A $SLURM_ACCOUNT"
      echo "#SBATCH -p $SLURM_PARTITION"
      echo "#SBATCH -q $SLURM_QOS"
      echo "#SBATCH --nodes=1"
      echo "#SBATCH --gpus-per-node=$SLURM_GPUS"
      echo "#SBATCH --ntasks-per-node=1"
      echo "#SBATCH --cpus-per-task=32"
      echo "#SBATCH --mem=256G"
      echo "#SBATCH -t ${WALLTIME:-20:00:00}"
      echo "#SBATCH --exclude=$SLURM_EXCLUDE"
      echo "set -uo pipefail"
      echo "source '$KIT/env.sh'"
      echo "mkdir -p \"\$TRITON_CACHE_DIR\""
      echo "echo \"[job] node=\$(hostname -s) model=\$MODEL_ID cell=${name}\""
      echo "pids=()"
      echo "for i in \$(seq 0 \$((SHARDS-1))); do"
      if [ "$shard_flag" = 1 ]; then
        echo "  CUDA_VISIBLE_DEVICES=\$i '$py' '$script' ${args[*]@Q} \\"
        echo "    --shard \"\$i/\$SHARDS\" > '$LOGS/${name}'_\"\$SLURM_JOB_ID\"_shard\$i.log 2>&1 &"
      else
        echo "  CUDA_VISIBLE_DEVICES=\$i '$py' '$script' ${args[*]@Q} \\"
        echo "    > '$LOGS/${name}'_\"\$SLURM_JOB_ID\"_shard\$i.log 2>&1 &"
      fi
      echo "  pids+=(\$!)"
      echo "done"
      # A bare `wait` returns only the LAST job's status, so a dead shard goes
      # unnoticed and the cell silently reports n=456 instead of 608. Check
      # every pid.
      echo "rc=0"
      echo "for i in \"\${!pids[@]}\"; do"
      echo "  if ! wait \"\${pids[\$i]}\"; then"
      echo "    echo \"[job] SHARD \$i FAILED -- see $LOGS/${name}_\${SLURM_JOB_ID}_shard\$i.log\""
      echo "    rc=1"
      echo "  fi"
      echo "done"
      echo "[ \$rc -eq 0 ] && echo '[job] all shards OK' || echo '[job] INCOMPLETE -- do not trust this cell'"
      echo "exit \$rc"
    } > "$sb"
    say "submitting $name  (model=$MODEL_TAG, $SHARDS shards)"
    sbatch "$sb" || fail "sbatch refused $name"
    note "watch it:  squeue -u \$USER        logs: $LOGS/${name}_<jobid>_shard0.log"
  else
    require_env "$py" "python"
    IFS=',' read -ra gpus <<< "$GPU"
    local n=${#gpus[@]}
    say "running $name locally on GPU(s) $GPU  ($n shard(s))"
    local pids=() i
    for i in $(seq 0 $((n-1))); do
      if [ "$shard_flag" = 1 ]; then
        CUDA_VISIBLE_DEVICES="${gpus[$i]}" "$py" "$script" "${args[@]}" \
          --shard "$i/$n" > "$LOGS/${name}_shard$i.log" 2>&1 &
      else
        CUDA_VISIBLE_DEVICES="${gpus[$i]}" "$py" "$script" "${args[@]}" \
          > "$LOGS/${name}_shard$i.log" 2>&1 &
      fi
      pids+=($!)
      note "shard $i/$n -> GPU ${gpus[$i]}  (log: $LOGS/${name}_shard$i.log)"
    done
    local rc=0
    for i in "${!pids[@]}"; do
      wait "${pids[$i]}" || { warn "shard $i FAILED -- see $LOGS/${name}_shard$i.log"; rc=1; }
    done
    [ $rc -eq 0 ] && say "$name done" || fail "$name INCOMPLETE -- do not trust this cell"
  fi
}

# Resolve a skill filename to a path, accepting either form.
skill_path() {
  case "$1" in
    /*) echo "$1" ;;
    *)  echo "$KIT/skills/$1" ;;
  esac
}
