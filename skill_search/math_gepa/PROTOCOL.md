# GEPA skills on the math suite: protocol (written 2026-11-01, before any skill was optimized)

## Goal
Does an optimizer (GEPA) find a skill that helps on the shortcut-free math suite, where hand-written
skills (livemath_ts, small_cases) and SkillOpt gave nothing beyond a placebo? Same rules as
rg_gepa/PROTOCOL.md, which found three robust skills on procedural Reasoning Gym tasks.

## Stack
The main-table stack: greedy, thinking off, 2048 new tokens, kit prompt + answer forcing.
Models Qwen3-8B and Qwen3-14B (27B left out: 4096 tokens, roughly double the GPU time).
Optimization runs on a vLLM server with prompts byte-identical to the runners
(mcq_math/evaluate_vllm_mcq.py, kit_v4/freemath/evaluate_vllm_freemath.py); test runs use the
runners themselves.

**Scoring fix found while setting this up:** the kit's free-form scorer needs `math_verify`, which
was not installed in any env on the box; its exceptions were caught and counted as wrong, so every
free-form cell so far was scored by string match only (0 symbolic or numeric matches in 12.5k
test records). math_verify is now installed in ~/rg_env. All free-form cells (old and new) are
rescored with it (`rescore_mv.py`, outputs in ~/budget/results_mv; originals untouched).

## Optimization (GEPA), per benchmark and model
Train split for reflection (MCQ: the 40 items in neither val nor test; free-form: fm_split train,
30–40 items), val split for selection (30–100 items), budget 1200 rollouts, minibatch 4,
reflection LM = the target model, seed skill "Solve the task step by step and check your work
before answering.", skills over 300 words score 0. The reflection prompt forbids copying problems,
numbers or answers and forbids rules for guessing from the wording of the options.
Output = GEPA's best-on-val candidate.

## Test (once per skill)
Test split of that benchmark, runner as in the main table. Conditions: GEPA skill and seed skill
(new); baseline, placebo_notation and brevity_control (existing cells, rescored).

A skill counts as **found** only if, on its benchmark's test split:
1. it beats baseline, placebo_notation, brevity_control and the seed skill (exact McNemar,
   Holm over these 4 tests within the cell, α = 0.05);
2. its gain over placebo_notation is at least 5 points;
3. its text has no literal problem fragment or answer from train/val (script check), and no
   option-guessing rule (read by hand, reported).
Also reported, not used to select: pooled suite result per model (each benchmark weighted
equally), val vs test gain, and how often replies hit the token limit.

If no cell passes, the result is "GEPA finds nothing on the math suite", reported as such.
