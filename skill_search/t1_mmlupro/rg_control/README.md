# Reasoning Gym SkillOpt positive control (2026-11-16)

SkillOpt (same stack as the MMLU-Pro runs: editor Qwen3.6-27B, starting skill = the one-liner) trained on a
Reasoning Gym task: train 60 questions (seed 11), validation 40 x 4 samples (seed 12), batch 60. Test: 200 fresh
questions (seed 100000). t=0 is greedy; t=1 is the mean of 3 runs at temperature 1.0. GEPA skill = the skill from
the earlier GEPA control on the same task (reference only). Scripts: `train_rg.sh`, `run_rg.sh`, `rgym_env/`.

| Model / task | Decoding | No prompt | One-liner (start) | SkillOpt | GEPA (ref) |
|---|---|---|---|---|---|
| Qwen3-8B / products | t=0 | 59.5 | 62.5 | 96.0 | 91.0 |
| Qwen3-8B / products | t=1 | 62.2 | 77.0 | 91.8 | 91.7 |
| Qwen3-14B / decimal_arithmetic | t=0 | 24.5 | 25.0 | 37.0 | 54.0 |
| Qwen3-14B / decimal_arithmetic | t=1 | 24.3 | 26.5 | 40.2 | 51.0 |

Trained skills: `skills/`. Per-question outputs stay on the box (`~/rg_gepa/skillopt_ctrl/`).
