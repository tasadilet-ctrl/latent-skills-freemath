#!/usr/bin/env bash
# Compare strength_audit against strength_audit_nometa across the full LiveMath
# matrix: 3 model sizes x 2 skills x {text, embed/dummy, embed/none}, plus a
# shared baseline per model.
#
#   ./sweep_skill_comparison.sh wave1     baselines + text cells + extractions
#   ./sweep_skill_comparison.sh wave2     fidelity sweeps  (needs wave1 vectors)
#   ./sweep_skill_comparison.sh wave3     embed cells      (needs wave2 picks)
#   ./sweep_skill_comparison.sh plan      print the plan, submit nothing
#
# WHAT THIS ABLATION ISOLATES
#   strength_audit's step 5 tells the model that meta-options ("one of the
#   other options is correct, but a stronger result can be proven") are real
#   claims. Per skills/notes/README.md that option appears in 263 of 608
#   questions and is ALWAYS correct when present, so a skill that simply
#   learns to pick it scores well without reasoning better.
#
#   strength_audit_nometa.md is byte-identical except step 5 is removed. So:
#     gain(strength_audit) - gain(nometa)  =  what naming the meta-option buys
#     gain(nometa)                         =  what the strengthening audit buys
#   If nearly all the gain sits in the first term, the skill is test-taking on
#   LiveMath's answer format, which is exactly the caveat Adilet flagged.
#
# WHY WAVES, NOT ONE SCRIPT
#   Embed cells need vectors; vectors need an operating point; the operating
#   point needs a fidelity sweep. Everything WITHIN a wave is independent and
#   is submitted at once -- on a contended cluster queue position is worth more
#   than tidy sequencing, and holding jobs back cost ~9 h on a previous run.
set -uo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$KIT/lib/common.sh"

# env.sh has ALREADY defaulted PY_EVAL/HF_HOME to paths inside the kit, so a
# "${PY_EVAL:-...}" fallback here would never fire. This machine's kit has no
# torch venv and no weight cache of its own -- both live in the qwen bundle --
# so override only when the kit's own copy is actually absent. A colleague who
# ran setup.sh, or who exports PY_EVAL themselves, is unaffected.
BUNDLE=/shared/home/adil.taibassarov/qwen_vllm_scripts_bundle_20260602
[ -x "$PY_EVAL" ]   || export PY_EVAL="$BUNDLE/.venv/bin/python"
[ -d "$HF_HOME" ]   || export HF_HOME="$BUNDLE/hf_cache"
export HF_HUB_OFFLINE=1

SKILLS="strength_audit strength_audit_nometa"
MODELS="Qwen/Qwen3-8B Qwen/Qwen3-14B Qwen/Qwen3.6-27B"
PLACEBO="placebo_matched.md"

# Per-model knobs. The 27B needs 4096 tokens: at 2048 it truncated 51.6% of
# replies mid-deliberation and scored 16.94% -- BELOW the 20% chance floor.
cfg() {
  case "$1" in
    *Qwen3-8B*)    echo "qwen3-8b 8 2048"    ;;
    *Qwen3-14B*)   echo "qwen3-14b 8 2048"   ;;
    *Qwen3.6-27B*) echo "qwen3.6-27b 4 4096" ;;
  esac
}

WAVE="${1:-plan}"

if [ "$WAVE" = plan ]; then
  cat <<'PLAN'

  WAVE 1  (no dependencies -- submit all at once)
      3 baselines          one per model, shared by both skills
      6 text cells         3 models x 2 skills
     12 extractions        3 models x 2 skills x {from placebo, from nothing}
     --
     21 jobs

  WAVE 2  (needs wave 1 vectors)
     12 fidelity sweeps    pick (layer, gamma) per vector by fidelity,
                           NOT by whichever accuracy looks best
  WAVE 3  (needs wave 2 picks)
     12 embed cells        3 models x 2 skills x {embed/dummy, embed/none}

  TOTAL 45 jobs. LiveMath is ~50 min of compute per eval cell on 4 GPUs;
  extractions and sweeps are shorter. Queue time dominates.

  Baselines are skill-independent and shared. They are re-run here rather than
  reused from record/ so the whole comparison sits on one software stack --
  the archived cells predate the current transformers build.

PLAN
  exit 0
fi

# checked only once we are actually going to submit something
require_env "$PY_EVAL" eval
require_data "$DATA/livemath.jsonl"
for s in $SKILLS; do
  [ -f "$KIT/skills/$s.md" ] || fail "missing skill: skills/$s.md"
done
submitted=0

if [ "$WAVE" = wave1 ]; then
  for M in $MODELS; do
    read -r TAG BS_M MAXNEW_M <<< "$(cfg "$M")"
    export MODEL_ID="$M" MODEL_TAG="$TAG" BS="$BS_M" MAXNEW="$MAXNEW_M"

    say "$TAG :: baseline"
    submit "livemath_${TAG}_baseline" "$PY_EVAL" "$KIT/src/evaluate.py" \
      --domain livemath --condition baseline --limit 608 \
      --batch-size "$BS" --max-new-tokens "$MAXNEW"
    submitted=$((submitted+1))

    for SK in $SKILLS; do
      say "$TAG :: text[$SK]"
      submit "livemath_${TAG}_text_${SK}" "$PY_EVAL" "$KIT/src/evaluate.py" \
        --domain livemath --condition text --skill "$KIT/skills/$SK.md" \
        --limit 608 --batch-size "$BS" --max-new-tokens "$MAXNEW"
      submitted=$((submitted+1))

      # Extraction is one forward pass per pool prompt -- one GPU is enough.
      say "$TAG :: extract $SK from placebo"
      NO_SHARD=1 SHARDS=1 SLURM_GPUS=1 WALLTIME=04:00:00 \
      submit "extract_${TAG}_${SK}_placebo" "$PY_EVAL" \
        "$KIT/src/extract_vectors.py" --pool neutral --n 50 \
        --skill "$KIT/skills/$SK.md" --baseline-skill "$KIT/skills/$PLACEBO"
      submitted=$((submitted+1))

      say "$TAG :: extract $SK from nothing"
      NO_SHARD=1 SHARDS=1 SLURM_GPUS=1 WALLTIME=04:00:00 \
      submit "extract_${TAG}_${SK}_none" "$PY_EVAL" \
        "$KIT/src/extract_vectors.py" --pool neutral --n 50 \
        --skill "$KIT/skills/$SK.md"
      submitted=$((submitted+1))
    done
  done
  say "wave 1 submitted: $submitted jobs"
  note "watch: squeue -u \$USER     then: ./sweep_skill_comparison.sh wave2"
  exit 0
fi

if [ "$WAVE" = extract ]; then
  # Just the 12 extractions. Exists because wave1 bundles them with the eval
  # cells, and re-running wave1 to recover an extraction failure would submit
  # nine duplicate benchmark runs that each overwrite a real result file.
  for M in $MODELS; do
    read -r TAG BS_M MAXNEW_M <<< "$(cfg "$M")"
    export MODEL_ID="$M" MODEL_TAG="$TAG"
    for SK in $SKILLS; do
      say "$TAG :: extract $SK from placebo"
      NO_SHARD=1 SHARDS=1 SLURM_GPUS=1 WALLTIME=04:00:00 \
      submit "extract_${TAG}_${SK}_placebo" "$PY_EVAL" \
        "$KIT/src/extract_vectors.py" --pool neutral --n 50 \
        --skill "$KIT/skills/$SK.md" --baseline-skill "$KIT/skills/$PLACEBO"
      submitted=$((submitted+1))
      say "$TAG :: extract $SK from nothing"
      NO_SHARD=1 SHARDS=1 SLURM_GPUS=1 WALLTIME=04:00:00 \
      submit "extract_${TAG}_${SK}_none" "$PY_EVAL" \
        "$KIT/src/extract_vectors.py" --pool neutral --n 50 \
        --skill "$KIT/skills/$SK.md"
      submitted=$((submitted+1))
    done
  done
  say "extractions submitted: $submitted jobs"
  exit 0
fi

if [ "$WAVE" = wave2 ]; then
  for M in $MODELS; do
    read -r TAG BS_M MAXNEW_M <<< "$(cfg "$M")"
    export MODEL_ID="$M" MODEL_TAG="$TAG"
    for SK in $SKILLS; do
      for ARM in placebo none; do
        # EXACT paths, never a glob. extract_vectors names the two arms
        # ..._placebo.pt and ..._plain.pt, and "strength_audit*" also matches
        # "strength_audit_nometa*" while "*${ARM/none/}*" degenerates to "**"
        # for the none arm -- so a glob here silently resolved the none arm to
        # the PLACEBO vector, running the wrong contrast under the right label.
        case "$ARM" in
          placebo) SUF=placebo ;;
          none)    SUF=plain   ;;
        esac
        VEC="$VECTORS/v_${TAG}_${SK}_neutral_n50_${SUF}.pt"
        [ -f "$VEC" ] || { warn "no $ARM vector for $TAG/$SK ($(basename "$VEC")) -- skipping"; continue; }
        EXTRA=()
        [ "$ARM" = placebo ] && EXTRA=(--baseline-skill "$KIT/skills/$PLACEBO")
        say "$TAG :: fidelity $SK/$ARM"
        NO_SHARD=1 SHARDS=1 SLURM_GPUS=1 WALLTIME=06:00:00 \
        submit "fid_${TAG}_${SK}_${ARM}" "$PY_EVAL" "$KIT/src/fidelity.py" \
          --vectors "$VEC" --skill "$KIT/skills/$SK.md" --probe livemath \
          --n 16 --mode relative "${EXTRA[@]}"
        submitted=$((submitted+1))
      done
    done
  done
  say "wave 2 submitted: $submitted jobs"
  note "when they finish, read the sweeps and pass the picks to wave3"
  exit 0
fi

if [ "$WAVE" = wave3 ]; then
  fail "wave 3 takes an operating point per vector, which must be CHOSEN, not
    guessed. Read the wave-2 fidelity output, pick the best fidelity among
    settings that pass 05_check_degeneration.sh, then launch each cell:

      ./run_embed_from_placebo.sh <vec> <layers> <gamma>
      ./run_embed_from_nothing.sh <vec> <layers> <gamma>

    Automating the pick would be choosing operating points by whatever number
    came out highest, which is the thing the fidelity protocol exists to avoid."
fi

fail "unknown wave '$WAVE' -- expected plan, wave1, wave2 or wave3"
