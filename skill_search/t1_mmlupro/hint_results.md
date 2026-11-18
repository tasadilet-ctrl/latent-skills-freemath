# Per-question hint diagnostic, T1 MMLU-Pro test (2026-11-17)

Before each of the 365 T1 test questions, Qwen3.6-27B (thinking on, T 0.6) wrote a hint of at most 60 words from
the question alone (no options, no answer); the hint is the system prompt for that question only. This estimates how
much any system prompt can add when it is tailored to the question. Mean of 5 runs at T 1.0 (`gen_hints.py`,
`run_hints.sh`). 48 questions got no hint (no system prompt) and 3 hints were flagged as leaking the answer
(gold option text or an announced answer); "clean" drops those 51. The hints are not committed (they quote the
test questions).

| Model | No skill | One-liner | Hint | Hint − no skill | Hint − no skill, clean (n=314) |
|---|---|---|---|---|---|
| Qwen3-4B | 67.8 | 69.8 | 72.3 | +4.5 | +4.6 |
| Qwen3-8B | 71.1 | 71.8 | 74.6 | +3.5 | +3.6 |
| Qwen3-14B | 76.0 | 77.1 | 79.9 | +3.9 | +4.4 |
| Qwen3.6-27B | 91.0 | 92.4 | 91.9 | +0.9 | +0.6 |

Forced answers fall by 2-3 points with hints. 27B gets hints written by itself, so it gains nothing new.
