# SkillOpt at temperature 1.0, 5 runs, on MMLU-Pro math

Repeats Adil's LiveMath experiment (`GUIDE_T1_5RUNS.md`, `adil` branch) on MMLU-Pro math. Per run R = 1..5:
4 SkillOpt trainings (answering model Qwen3-4B / 8B / 14B / Qwen3.6-27B, editor Qwen3.6-27B, both at T 1.0,
`train.seed=R`), then no skill + the 4 skills tested on all 4 models at T 1.0 with engine seed R.

| file | what |
|---|---|
| `patch_mcqkit.py` | builds the `mcqkit` SkillOpt env from `mcqmath`: rollouts use the test runner's prompt (skill as the whole system prompt, the runner's question/options text and `Answer: <letter>` line, chat template with thinking off, completions endpoint), its answer forcing and its parser; options not shuffled; 2048 tokens (27B 4096) |
| `train_one.sh <size> <R>` | one training on the box: target on GPU 0, editor on GPU 1, FlashInfer |
| `evaluate_mcq_t1.py` | the test runner at T 1.0 (prompt/parser imported from `mcq_math/evaluate_vllm_mcq.py`), files in the guide's layout for `make_runs_table_png.py` |
| `run_t1.sh <first> <last>` | restartable driver for the runs; waits for free GPUs |

Differences from the guide:
- **Split:** the paper's pre-registered split (train 40 / val 100 / test 365), with batch 40 = the whole train split. The guide uses 60 / 40. This keeps the held-out set equal to the paper's test set and gives a less noisy gate.
- **Hardware:** a 2-GPU workstation, so the trainings run one at a time.

Found during the smoke test: importing `transformers` inside the 64 rollout threads failed at random, and those items were scored wrong. On 16 val items the baseline scored 12.5% instead of about 80%, so the gate accepted anything. `transformers` is now imported once, at module load.
