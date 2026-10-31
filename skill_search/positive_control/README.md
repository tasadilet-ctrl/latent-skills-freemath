# Positive control: procedural skills that work as text, and their vectors

Why: on the shortcut-free math suite no text skill beats a placebo (`../budget/PROTOCOL.md`),
and any prompt change only reshuffles the same ~10% of borderline questions, so the vector arm
had no effect to carry. Here the skill supplies a procedure the model does not follow by itself.

Tasks (generated, exact gold, `pilot.py`): letter counting in 8–12 words, 5-digit × 5-digit
multiplication, weekday of a date (Zeller), base-7 conversion. Skills in `skills/`; placebo =
`placebo_notation` (length-matched, no procedure). Greedy, thinking off, 2048 tokens.

## Pilot (vLLM, 150 items per task, `pilot_results.txt`)

| task | model | none | placebo | text skill |
|---|---|---|---|---|
| count | 8B / 14B | 22 / 31 | 19 / 25 | **97 / 89** |
| mult | 8B / 14B | 7 / 31 | 7 / 1 | **58 / 65** |
| weekday | 8B / 14B | 39 / 27 | 44 / 57 | 31 / 59 (placebo matches: not a skill effect) |
| base7 | 8B / 14B | 98 / 98 | 93 / 97 | 99 / 95 (ceiling) |

## Vector arm on count and mult (HF engine, `vec_posctl.py`, `vector_report.txt`)

Same design as `../vector_mcq/` (B1 = skill − placebo, B2 = skill − nothing, CONTROL = placebo −
nothing; 40 train items; 8B L34, 14B L37, γ = 0.3, fixed in advance). Accuracy %, test n = 150:

| | none | placebo | text | B1 | B2 | CONTROL |
|---|---|---|---|---|---|---|
| count 8B | 18.0 | 17.3 | **96.0*** | 13.3 | 16.0 | 16.0 |
| count 14B | 30.0 | 26.7 | **90.0*** | 28.0 | 31.3 | 26.7 |
| mult 8B | 6.7 | 6.7 | **56.0*** | 23.3* | **57.3*** | 31.3* |
| mult 14B | 26.0 | 1.3* | **67.3*** | 39.3* | 20.0 | 2.7* |

What the steered replies do:
* **Counting: the vectors carry nothing.** The text skill makes the model spell each word with
  hyphens (141/150 replies) and reach 96%; no vector produces the spelling (0–2/150) or a gain.
* **Multiplication: the vectors carry a mode, not the procedure.** 8B B2 matches the text
  skill (57.3 vs 56.0, beats CONTROL p = 3e-6) with a third of the length, but by the model's own
  distributive decomposition — 14/150 replies mention partial products vs 150/150 with the text.
  CONTROL alone gives +25 on the 8B, so part of it is "a system prompt is present".
* **Vectors do carry a global behaviour faithfully when the prompt has one**: the placebo makes
  the 14B answer multiplication in one line (24 chars, 1.3%); the CONTROL vector reproduces it
  (33 chars, 2.7%; fidelity 0.69).

Reading: a steering vector transfers *how much / how carefully* the model works, not *which
steps* a skill prescribes. A skill whose value is a specific procedure (count) does not survive
as a vector; one whose value is mostly "work it out instead of guessing" (mult) partly does.
