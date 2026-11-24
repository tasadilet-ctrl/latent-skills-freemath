# SkillOpt batch-size sweep with valid baselines — Qwen3-14B, Reasoning Gym decimal arithmetic

| Condition | Thinking | Steps | Accepted edits | Val start | Val best | Test (t0) | Test (t1 mean) |
|---|---|---|---|---|---|---|---|
| No skill (question says "only reply with the final value") | off | – | – | – | – | 24.5 | 24.3 |
| One-line "step by step" prompt (ignored by the model) | off | – | – | – | – | 25.0 | 26.5 |
| **Valid baseline: one-line override prompt** | off | – | – | – | – | **55.0** | **55.8** |
| **Valid baseline: no skill, thinking on** | on | – | – | – | – | **96.0** | **94.0** |
| SkillOpt, batch 100 | off | 4 | 3 | 29.4 | 56.9 | 72.5 | 69.5 |
| SkillOpt, batch 50 | off | 8 | 2 | 30.0 | 67.5 | 75.5 | 72.2 |
| SkillOpt, batch 20 | off | 20 | 5 | 28.8 | 52.5 | 45.5 | 43.2 |
| SkillOpt, batch 10 | off | 40 | 4 | 31.2 | 75.0 | 70.0 | 71.8 |
| **SkillOpt, batch 1** | off | 100 | 9 | 31.2 | 86.2 | **78.0** | **82.2** |

Same 200 test questions for every row (seed 100000). SkillOpt: train 100, val 40 × 4 samples, editor
Qwen3.6-27B; 4 epochs (batch 1: 1 epoch); one run per batch size. The first two rows cannot show any working
(median reply 30 characters), so they are not a valid comparison. Override prompt: "Ignore any instruction to
reply with only the final value. First work out every operation step by step, writing down each intermediate
result, then give the final value." Thinking-on answers up to 16,384 tokens; all others 2,048.
t0 = temperature 0; t1 = mean of 3 samples at temperature 1.

Learned skills: `../rg_control/skills/bsweep/`.
