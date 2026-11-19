# Reasoning Gym SkillOpt positive control

SkillOpt, same stack as the MMLU-Pro runs: Qwen3.6-27B edits (thinking on), the target answers with thinking off,
both at T 1.0; starting skill = the one-liner "Solve the task step by step and check your work before answering."
Validation: 40 questions (seed 12), each scored 4 times. Test: 200 fresh questions (seed 100000). "t=0" is greedy;
"t=1" is the mean of 3 runs at temperature 1.0. Per-question outputs stay on the box (`~/rg_gepa/skillopt_ctrl/`).

## First run (2026-11-16): train 60 (seed 11), batch 60, 4 epochs (`run_rg.sh`)

| Model / task | Decoding | No prompt | One-liner (start) | SkillOpt |
|---|---|---|---|---|
| Qwen3-8B / products | t=0 | 59.5 | 62.5 | 96.0 |
| Qwen3-8B / products | t=1 | 62.2 | 77.0 | 91.8 |
| Qwen3-14B / decimal_arithmetic | t=0 | 24.5 | 25.0 | 37.0 |
| Qwen3-14B / decimal_arithmetic | t=1 | 24.3 | 26.5 | 40.2 |

## Batch-size sweep (2026-11-18/19): Qwen3-14B, decimal_arithmetic, train 100 (seed 11) (`run_bsweep.sh`)

4 epochs each (400 training examples seen), except batch 1: 1 epoch (100 steps). One training run per batch size.

| Batch | Steps | Edits accepted | Val best (start 29-31) | Test t=0 | Test t=1 |
|---|---|---|---|---|---|
| 100 | 4 | 3 | 56.9 | 72.5 | 69.5 |
| 50 | 8 | 2 | 67.5 | 75.5 | 72.2 |
| 20 | 20 | 5 | 52.5 | 45.5 | 43.2 |
| 10 | 40 | 4 | 75.0 | 70.0 | 71.8 |
| 1 | 100 | 9 | 86.2 | 78.0 | 82.2 |

Validation ranks the runs the same way test does (unlike MMLU-Pro). With one run per batch size the ordering
other than batch 1 is not resolved (batch 20 is most likely a bad run), and the jump over the first run also
reflects 100 vs 60 training questions. Trained skills: `skills/` (first run) and `skills/bsweep/`.
