# SkillOpt on free-form math: BeyondAIME, HARDMath2, RealMath

The `skillopt_local/` pipeline (SkillOpt @343db22, Qwen3.6-27B optimizer, local
vLLM) was wired for LiveMath only. This folder runs the same pipeline on three
**free-form final-answer** benchmarks.

Why free-form: LiveMath is multiple choice, and its options have two answer-format
shortcuts (`../../PROTOCOL.md`). One is the meta-option "One of the remaining
options is correct, but a stronger result can be proven", which is correct 263/263
times. The other is the similarity centroid. Without answer options there is no
option structure to exploit. On LiveMath, SkillOpt wrote the meta-option rule
straight into its skill (README section 9).

| benchmark | source | items | split (train/val/test) | answers |
|---|---|---|---|---|
| BeyondAIME | `ByteDance-Seed/BeyondAIME` | 100 | 30 / 30 / 40 | integers |
| HARDMath2 | `JVRoggeveen/HARDMath2` | 211 | 40 / 50 / 121 | asymptotic formulas |
| RealMath | `ethz-spylab/RealMath` (Math_arXiv) | 387 kept of 633 | 40 / 60 / 287 | expressions |
| ArxivMath | `MathArena/arxivmath` | 103 | 30 / 30 / 43 | not in the default run, see below |

The split is a deterministic hash of the item id. The ids are in `ids_freemath.json`;
the data itself is not committed. RealMath keeps only single-expression answers under
120 characters, because the automatic checker cannot score multi-part or case-split
answers.

## Files

| file | what it does |
|---|---|
| `env/` | the SkillOpt env `freemath`: loader, rollout, scorer, prompts, seed skill |
| `configs/default.yaml` | its SkillOpt config |
| `install_env.sh` | copies `env/` into a SkillOpt checkout and registers it in `train.py` and `eval_only.py` (idempotent) |
| `make_split_freemath.py` | downloads the four benchmarks and writes `<work>/fm_split/<bench>/{train,val,test}/items.json` |
| `run_freemath_local.sh` | workstation version of `../run_skillopt.sbatch`. Two vLLM servers, then SkillOpt per benchmark, then the final comparison. `SMOKE=1` runs the plumbing check |
| `run_final_forced.sh` | the final comparison again, with the forcing pass on (`env.force_answer=true`) |
| `rescore_freemath.py` | re-applies the current scorer to saved replies, with no new generations |
| `analyze_freemath.py` | the final table: paired exact McNemar against no-skill, per benchmark and task type |

## Run

```bash
W=~/skillopt_work                                     # SkillOpt + vllm_env as in ../setup.sh
freemath/install_env.sh $W/SkillOpt
cd $W/SkillOpt && .venv/bin/python <kit>/skill_search/skillopt_local/freemath/make_split_freemath.py $W
SMOKE=1 <kit>/.../freemath/run_freemath_local.sh Qwen/Qwen3-8B arxivmath     # minutes
<kit>/.../freemath/run_freemath_local.sh Qwen/Qwen3-8B                      # hours
<kit>/.../freemath/run_final_forced.sh Qwen/Qwen3-8B
.venv/bin/python <kit>/.../freemath/rescore_freemath.py $W qwen3-8b
.venv/bin/python <kit>/.../freemath/analyze_freemath.py $W qwen3-8b final_eval_forced
```

The final comparison scores four conditions on the identical test items, with the
same server and the same prompt: `none` (no skill), `placebo` (`skills/placebo_matched.md`),
`strength_audit` (`skills/strength_audit.md`) and `skillopt` (the learned `best_skill.md`).
SkillOpt's own `summary.json` test score is not used. Run to run it varied by
±2 items out of 40 for the *same* skill, because vLLM batching under concurrency is
not deterministic.

## Pitfalls found while building this

1. **math-verify does not work in threads.** Its timeouts use `signal.alarm()`.
   SkillOpt's rollout scores replies in a thread pool, so every symbolic and numeric
   check raised, and the scorer quietly returned "wrong". Only exact string matches
   counted. HARDMath2's val baseline read 0/50 when it was not. Fix: math-verify's
   timeouts are off, and each comparison runs under our own deadline
   (`env/evaluator.py`, `_with_deadline`). Runs made before the fix are kept as
   `*_bugged_scorer` and are not reported.
2. **Gold-answer delimiters.** RealMath writes answers as `\( 0 \)` and `\[ … \]`.
   These are stripped now, and right-hand sides of equations are compared too
   (`\omega = 1` vs `1`).
3. **Truncation.** At a 4096-token budget, 17–25% of BeyondAIME replies never reach a
   final `\boxed{}`, and the rate differs by condition. The kit's `evaluate.py` forces
   an answer in that case and SkillOpt's rollout did not. `force_answer` restores it.
   It is off during training, so all training runs match, and on in
   `run_final_forced.sh`.
4. **A 6-digit decimal is not an exact rational.** math-verify's default tolerance
   accepts 0.428571 for 3/7, so `float_rounding=10` is set. The numeric check applies
   only to formulas with free symbols.
5. **Floor effects.** Qwen3-8B with thinking off scored 0/16 on ArxivMath's val split
   in the smoke run, so the gate had nothing to compare. ArxivMath is therefore out of
   the default run; use it with a stronger target.
6. **The optimizer memorises.** In the smoke run it added "Polarize identities: for
   x^k=0, expand (x+y)^k=0 … the exact nilpotency index", which comes from one
   training question. Read every `best_skill.md` line by line.

## Results

Qwen3-8B target, thinking off. **The corrected run is in progress.** These are
interim numbers on the unforced test split, re-scored with the final scorer:

| benchmark | none | placebo | strength_audit | skillopt | SkillOpt kept |
|---|---|---|---|---|---|
| BeyondAIME (n=40) | 2.5 | 5.0 | 10.0 | 5.0 | seed skill (0 of 4 edits accepted) |

HARDMath2 and RealMath are being re-run with the thread-safe scorer. The numbers
will land here.
