# SkillOpt on LiveMath (option-1 split, OTHER questions) — Qwen3-4B, our box

| Run | Steps | Accepted at step | Val start | Val best | Skill length (words) | Test OTHER (224 q) | vs no skill | Test META (232 q) |
|---|---|---|---|---|---|---|---|---|
| **No skill** | – | – | – | – | – | **38.8** (35.7 / 40.6 / 40.2) | – | 0.1 |
| 1 | 4 | none (starting skill kept) | 52.5 | 52.5 | 154 | 39.3 | +3.6 | 0.9 |
| 2 | 4 | 2 | 52.5 | 60.0 | 298 | 48.7 | +8.1 | 0.9 |
| 3 | 4 | 1 | 35.0 | 50.0 | 505 | 46.9 | +6.7 | 0.4 |
| **Mean** | | | | | | **45.0** | **+6.1** | 0.7 |

Train 60 / val 40 (OTHER questions only, outside SkillOpt's original 52, sha256 order); batch 60 = 1 step per epoch, 4 epochs;
editor Qwen3.6-27B; starting skill = LiveMath config's default heuristics (154 words); 16,384 completion tokens in training.
Test: 456 livemath556 questions outside train+val, T 1.0, seed = run number, no skill re-run with each seed.
META = questions whose correct option is "a stronger result can be proven"; the 4B never picks it. Adil's result: +5.4.
Run 1 accepted no edit, so its gain comes from the starting skill. Placebo control and runs 4–5 are queued.
