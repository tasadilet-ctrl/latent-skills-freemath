# Vector arm on the five GEPA skills (2026-11-01)

Same design as positive_control (B1 = skill − placebo_notation, B2 = skill − nothing, CONTROL =
placebo − nothing; diff-in-means at the last prompt token over 40 train items, seed 21;
h += 0.3·‖h‖·v̂ at 8B L34 / 14B L37; every cell on the HF engine). Test = the GEPA test items
(seed 0, n=200), dumped once to `items/` so every condition sees identical questions.
Scored with Reasoning Gym (`rescore_rg.py`). Full output: `vector_report.txt`.

| model | task | none | placebo | text | B1 | B2 | CONTROL |
|---|---|---|---|---|---|---|---|
| 14B | decimal_arithmetic | 24.0 | 21.5 | 58.0* | **55.5*** | **56.0*** | 22.5 |
| 8B | products | 55.0 | 48.0* | 92.0* | **87.5*** | 76.0* | 48.0* |
| 14B | products | 44.5 | 45.0 | 96.5* | 48.0 | 49.0* | 45.0 |
| 8B | polynomial_multiplication | 17.5 | 16.5 | 53.0* | 21.0 | 30.5* | 39.0* |
| 8B | word_sorting | 30.5 | 23.5* | 49.0* | 30.0 | 25.0 | 31.0 |

* p<0.05 vs none (exact McNemar). Key pairs: decimal B1 vs text +3/−8 (p=0.23), B2 vs CONTROL
+69/−2; products 8B B1 vs text +9/−18 (p=0.12), B1 vs CONTROL +79/−0.

Procedure trace (`trace_report.txt`, replies using the skill's own terms):
decimal 14B "significant digit / 12 digits / full precision": none 3, text 152, B1 173, B2 161;
products 8B "distributive": none 5, text 179, B1 74, B2 75; products 14B: text 100, B1 7, B2 12.

Reading: on two of five skills a vector reproduces the text skill (decimal 14B fully, products 8B
nearly), and on decimal the replies follow the skill's specific instructions. On products 14B and
word sorting vectors carry nothing; word-sorting vectors break answer termination (69/96 forced).
Polynomial: the CONTROL (placebo) vector helps most — the placebo is about notation, and part of
that skill's gain is answer syntax.

Note: Reasoning Gym's polynomial_multiplication generator is not reproducible across Python
processes (hash-seed dependent); the other three tasks are. Here it is scored from the asked
question with sympy (agrees with RG's scorer 400/400). In `../report_test.txt` each condition ran in
its own process, so polynomial accuracies are valid but its paired p-values are not; unpaired,
53.0 vs 14.5 (placebo) and 11.5 (seed) are still p<1e-15.
