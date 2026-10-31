# Search for a skill that beats livemath_ts — protocol (written 2026-10-28, before any run)

## Why a new skill

livemath_ts changes nothing on the shortcut-free suite (README result 4–5), so its vector
arm has no effect to carry. Failure analysis of the saved baseline replies (test splits,
same stack) shows where the models actually lose points: **they run out of tokens**.

| | share of replies hitting the token limit | accuracy when cut off | when finished |
|---|---|---|---|
| SuperGPQA 8B / 14B | 39% / 39% | 13 / 16 | 50 / 47 |
| MMLU-Pro 8B / 14B | 10% / 12% | 21 / 27 | 79 / 82 |
| IMO-AnswerBench 8B / 14B / 27B (forced) | 43 / 49 / 74% | 9 / 10 / 18 | 21 / 22 / 72 |
| BeyondAIME 27B (forced) | 80% | 12 | 62 |

The cut-off replies are mostly brute force: tabulating terms by hand, testing n = 518, 519,
520 … one by one, re-deriving. The placebos cut truncation (39% → 10%) but **lower**
accuracy, so being shorter is not the fix; the target is spending tokens on a better route.

## Drafts (skill_search/budget/skills/, all format-neutral, ~200–230 words)

* `route_first`   — pick the cheapest route before computing; structure over enumeration;
  switch routes when stuck; finish with the answer.
* `small_cases`   — exact small cases → pattern → check one more → apply.
* `check_answer`  — after a candidate, one or two independent cheap checks (limit, small
  instance, substitution, magnitude); use listed options to check only if there are any.
* `route_first_short` — route_first in ~90 words.

None mentions option similarity, a meta-option, or any benchmark. Each says: if options are
listed use them only to check, and if none are listed never refer to options (the
livemath_ts failure on free-form).

## Controls

* `placebo_notation` (existing, 216 words): presentation advice, **no length advice**.
* `brevity_control` (new): only "be concise, avoid unnecessary steps, always finish with the
  answer line". A draft whose gain is only "be shorter" will not beat it.

## Dev selection (fixed now)

Dev = MCQ ids_val (100 + 100) + free-form val (30 + 30 + 50 + 100 + 60) = 470 items per
model; models Qwen3-8B, Qwen3-14B, Qwen3.6-27B; same stack as the main table
(evaluate_vllm_mcq.py / evaluate_vllm_freemath.py, greedy, thinking off, kit prompt +
forcing, 2048 tokens, 4096 for the 27B).

Score = pooled dev accuracy gain over baseline (items weighted equally across the 7
benchmarks), averaged over the 3 models. Chosen draft = highest score, **provided** it is
also above both controls on that score and above baseline on at least 2 of 3 models. Ties
(within 0.5 points) → shorter text. If no draft qualifies, the result is "none found" and
nothing goes to test.

## Test (once, chosen draft only)

All 7 test splits × 3 models: chosen draft, placebo_notation, brevity_control (baseline
and livemath_ts already exist on the same stack). Report per cell and pooled; exact
McNemar vs baseline and vs each control; Holm within row as in the paper.

## Outcome (2026-10-28)

Dev (`report_dev.txt`) chose `small_cases` at +0.14 points (best control −0.21). Test
(`report_test.txt`, 1421 items per model, pooled):

| | 8B | 14B | 27B |
|---|---|---|---|
| small_cases vs no skill | −3.5 (p=0.001) | +1.0 (p=0.33) | +0.4 (p=0.71) |
| small_cases vs placebo_notation | −0.1 | +0.3 | +0.1 |
| small_cases vs brevity_control | +2.1 (p=0.04) | +4.6 (p<0.001) | −1.1 |
| small_cases vs livemath_ts | +1.5 (p=0.18) | +1.7 (p=0.12) | −0.8 |

No better skill found: small_cases is indistinguishable from the neutral placebo on every
model, and any system prompt costs the 8B ~3.5 points. It avoids livemath_ts's free-form
format failures, but that is not a procedural gain. route_first's 27B dev gain (+3.0) was
mostly matched by the brevity control (+2.3) and was not taken to test (not chosen).
