# SkillOpt epoch test — Qwen3-4B, MMLU-Pro math (T2 split), batch 100

| Epochs | Steps | Accepted at step | Val start | Val best | Skill length (words) | Test (255 q) | vs no skill |
|---|---|---|---|---|---|---|---|
| **No skill** | – | – | – | – | – | **68.2** | – |
| 4 (T2 run 1) | 4 | 1, 2 | 60.2 | 71.5 | 444 | 67.8 | −0.4 |
| 8 | 8 | 1, 2, 5 | 62.8 | 69.7 | 1,116 | 66.3 | −1.9 |
| 12 | 12 | 1, 2, 3, 4, 5, 10 | 61.5 | 68.8 | 1,895 | 67.1 | −1.1 |
| 20 | 20 | 1, 20 | 64.3 | 71.2 | 1,126 | 66.3 | −1.9 |

Train 100 / val 150 × 4 samples / test 255; batch 100 = 1 step per epoch; editor Qwen3.6-27B; starting skill =
SkillOpt's generic one; seed 1; one run per setting. Test at T 1.0, seed 1. Test noise ≈ ±3 points (4B no-skill
was 72.2 in another run with the same seed); val start varies 60–64 from sampling alone.
