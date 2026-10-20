# Vector cosines: livemath_ts

Cosine similarity between vectors, at three depths per model. 1.00 = same direction; random pairs give about ±0.02.

## qwen3-14b (40 layers)

layer 20

| | ours vs placebo | ours vs nothing | reply A | reply B | step A | step B |
|---|---|---|---|---|---|---|
| ours vs placebo | +1.00 | +0.45 | -0.10 | -0.15 | -0.01 | -0.09 |
| ours vs nothing | +0.45 | +1.00 | -0.06 | -0.03 | +0.06 | +0.11 |
| reply A | -0.10 | -0.06 | +1.00 | +0.88 | -0.17 | -0.02 |
| reply B | -0.15 | -0.03 | +0.88 | +1.00 | -0.15 | +0.13 |
| step A | -0.01 | +0.06 | -0.17 | -0.15 | +1.00 | +0.73 |
| step B | -0.09 | +0.11 | -0.02 | +0.13 | +0.73 | +1.00 |

layer 36

| | ours vs placebo | ours vs nothing | reply A | reply B | step A | step B |
|---|---|---|---|---|---|---|
| ours vs placebo | +1.00 | +0.49 | -0.07 | -0.07 | +0.04 | +0.01 |
| ours vs nothing | +0.49 | +1.00 | -0.22 | -0.15 | +0.07 | +0.06 |
| reply A | -0.07 | -0.22 | +1.00 | +0.91 | -0.05 | -0.05 |
| reply B | -0.07 | -0.15 | +0.91 | +1.00 | -0.05 | +0.00 |
| step A | +0.04 | +0.07 | -0.05 | -0.05 | +1.00 | +0.80 |
| step B | +0.01 | +0.06 | -0.05 | +0.00 | +0.80 | +1.00 |

layer 38

| | ours vs placebo | ours vs nothing | reply A | reply B | step A | step B |
|---|---|---|---|---|---|---|
| ours vs placebo | +1.00 | +0.41 | -0.03 | -0.05 | +0.04 | +0.02 |
| ours vs nothing | +0.41 | +1.00 | -0.22 | -0.17 | +0.12 | +0.09 |
| reply A | -0.03 | -0.22 | +1.00 | +0.92 | -0.13 | -0.10 |
| reply B | -0.05 | -0.17 | +0.92 | +1.00 | -0.10 | -0.03 |
| step A | +0.04 | +0.12 | -0.13 | -0.10 | +1.00 | +0.80 |
| step B | +0.02 | +0.09 | -0.10 | -0.03 | +0.80 | +1.00 |

