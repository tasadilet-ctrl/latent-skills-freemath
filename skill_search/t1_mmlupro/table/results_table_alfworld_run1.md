# ALFWorld — SkillOpt, run 1

| Model | Method | ALFWorld (%) | Δ vs no skill |
|---|---|---|---|
| Qwen3-4B | No skill | 28.4 | – |
| | SkillOpt | **55.2** | +26.9 |
| Qwen3-8B | No skill | 46.3 | – |
| | SkillOpt | **74.6** | +28.4 |
| Qwen3-14B | No skill | 45.5 | – |
| | SkillOpt | **79.9** | +34.3 |

134 test games (valid_unseen), one test pass, T 1.0, target thinking on. SkillOpt: batch 40 (all 39 train games), 4 epochs,
18 val games, editor Qwen3.6-27B. Each skill tested on the model that trained it.
