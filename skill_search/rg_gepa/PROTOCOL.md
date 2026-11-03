# GEPA skills on Reasoning Gym: protocol (written 2026-10-31, before any skill was optimized)

## Goal
Find skills with large gains that cannot come from shortcuts: generated instances with exact
checkers, an optimizer instead of hand-written skills, and controls fixed in advance.

## Stack
vLLM server (Qwen3-8B / Qwen3-14B, bf16, greedy, thinking off, 2048 tokens, forced `<answer>` on
cut-off replies). Skill = system prompt. Scoring = Reasoning Gym `score_answer`, correct iff 1.0.

## Task screen
36 procedural tasks at default difficulty, seed 1, n=60, no system prompt. A task enters
optimization if baseline accuracy is between 10% and 60% on the model. Screen seed is not reused.

## Optimization (GEPA)
Per task and model: train seed 11 (n=60) for reflection, val seed 12 (n=40) for selection,
budget 1200 rollouts, minibatch 4, reflection LM = the target model itself (no stronger model),
seed skill "Solve the task step by step and check your work before answering."
Skills over 300 words score 0. Output = GEPA's best-on-val candidate.

## Test (once per selected skill)
Test seed 0, n=200, default difficulty; plus a harder split (config chosen per task before the
test run, written to `hard_configs.json`) n=200.
Conditions: no skill, GEPA skill, the seed skill, placebo_notation (length-matched placebo),
brevity_control.

A skill counts as **found** only if, on the default-difficulty test:
1. it beats no skill, placebo_notation and the seed skill, exact McNemar, Holm within task (3 tests);
2. gain over placebo_notation is at least 10 points;
3. its text contains no literal instance or answer from train/val (checked by script);
4. replies follow it (trace check by a phrase the skill prescribes, reported per skill).
Harder-split result is reported for every found skill, not used to select.

## Vector arm
Every found skill gets the B1/B2/CONTROL vector test as in positive_control.

## Outcome (2026-10-31)

`report_test.txt` (test seed 0, n=200). Five skills pass every rule:

| model | task | no skill | placebo | seed skill | GEPA skill | hard split: none → GEPA |
|---|---|---|---|---|---|---|
| 8B | products (multiplication) | 54.5 | 49.5 | 62.0 | **92.0** | 0.0 → 29.5 |
| 8B | polynomial_multiplication | 16.5 | 14.5 | 11.5 | **53.0** | 2.5 → 15.5 |
| 8B | word_sorting | 32.0 | 22.0 | 35.5 | **52.0** | 2.0 → 6.5 |
| 14B | products | 45.0 | 44.5 | 54.5 | **95.5** | 0.0 → 60.0 |
| 14B | decimal_arithmetic | 24.0 | 21.5 | 26.5 | **56.0** | 0.0 → 30.5 |

Checks (`format_check.txt`): products and decimal_arithmetic baselines answer in one line (~30 chars)
with wrong digits, the GEPA skill makes them compute (500–1200 chars); no format-only misses.
Caveat: the polynomial skill also fixes answer syntax (`*`, `**`); 18/200 baseline replies gave no
parsable answer, so part of that gain is format. Word sorting skill adds a fact (ASCII order:
uppercase before lowercase). Leak-check hits (family_relationships, rotate_matrix,
binary_alternation) are generic words/numbers and none of those skills passed anyway.

Correction (2026-11-01): polynomial_multiplication items differ between Python processes, so its
paired McNemar p-values above are invalid (accuracies are valid; unpaired tests still p<1e-15).
The other four found skills use reproducible generators. See vec/README.md.

## Arm checks (2026-11-01, `checks_report.txt`)

* Item overlap: Reasoning Gym item i of seed s is generated from seed s+i, so GEPA train (seed 11)
  and val (seed 12) and the vector pool (seeds 21/22) are test items 11–70 of seed 0. On the 130
  never-used test items all four reproducible skills still pass, and the vector results hold.
* Fresh test, seed 100000 (no possible overlap), vLLM, n=200: products 8B 60.0 → 89.0, products 14B
  50.0 → 95.5, decimal 14B 24.5 → 52.5 (all p<1e-13 vs none/placebo/seed skill); word sorting 8B
  36.5 → 48.0 (vs none p=0.0008, vs placebo p=1e-8, vs seed skill 41.5 p=0.09: not significant).
* Random-direction vectors (same per-layer norm as B1, 2 seeds) give baseline accuracy:
  decimal 14B 22.5/24.0 (B1 55.5), products 8B 53.5/53.0 (B1 87.5).
