# SkillOpt batch-size sweep — Qwen3-14B (thinking off), Reasoning Gym decimal arithmetic

| Condition | Steps | Accepted edits | Val start | Val best | Test (t0) | Test (t1 mean) |
|---|---|---|---|---|---|---|
| **Baseline (no skill)** | – | – | – | – | **24.5** | **24.3** |
| One-line prompt | – | – | – | – | 25.0 | 26.5 |
| SkillOpt, batch 100 | 4 | 3 | 29.4 | 56.9 | 72.5 | 69.5 |
| SkillOpt, batch 50 | 8 | 2 | 30.0 | 67.5 | 75.5 | 72.2 |
| SkillOpt, batch 20 | 20 | 5 | 28.8 | 52.5 | 45.5 | 43.2 |
| SkillOpt, batch 10 | 40 | 4 | 31.2 | 75.0 | 70.0 | 71.8 |
| **SkillOpt, batch 1** | **100** | **9** | **31.2** | **86.2** | **78.0** | **82.2** |

Same 200 test questions for every row (Reasoning Gym seed 100000). Train 100, val 40 × 4 samples, editor
Qwen3.6-27B; 4 epochs (batch 1: 1 epoch); one run per batch size. Val start = SkillOpt's starting skill on val.
t0 = temperature 0; t1 = mean of 3 samples at temperature 1.

Baseline note: the questions say "Only reply with the final value", so with no skill the model answers at once
without working (median reply 30 characters). Most of SkillOpt's gain comes from skills that make it work the
calculation out step by step.

Image: `rg_batch_sweep.png`. Learned skills: `../rg_control/skills/bsweep/`.
