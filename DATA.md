# Data

**No benchmark data is redistributed in this repository.** The code to fetch and
prepare each dataset ships; the data itself does not. `00_setup/02_benchmark_data.sh`
runs the preparation step for all three.

Two reasons, and the first is not negotiable:

1. **OfficeQA is gated.** `databricks/officeqa` is `gated: auto` on Hugging Face.
   Republishing its questions would breach the terms accepted in order to
   download it.
2. **Publishing an answer key contaminates a live benchmark.** These files hold
   full questions *with* correct answers. A public copy ends up in the next
   generation of training corpora, and the benchmark stops measuring anything.

---

## LiveMath (LiveMathematicianBench)

608 research-level mathematics questions, 5-way multiple choice.

**Not automatically downloadable.** `data/prepare_livemath.py` builds
`data/livemath.jsonl` from monthly raw files it expects to find alongside it:

```
data/lm_202511.json  …  data/lm_202606.json      (8 files)
```

Obtain those from the benchmark authors, drop them in `data/`, then:

```bash
.venv/bin/python data/prepare_livemath.py
```

The preparation step is not cosmetic. In the raw files the correct choice is
labelled `A` in **all 608 questions** — the letters encode canonical roles
(A = correct, C = weaker-true, D = wildcard trap), not a presentation order.
Served unshuffled, "always answer A" scores 100%. `prepare_livemath.py` shuffles
the options with a per-question deterministic seed: reproducible across runs and
conditions, not guessable.

If you run against unshuffled data, every number is meaningless. Expect the
baseline near 20% (chance), not near 100%.

## SpreadsheetBench

400 spreadsheet-editing tasks with golden workbooks, from
`RUCKBReasoning/SpreadsheetBench` (public).

```bash
./00_setup/02_benchmark_data.sh spreadsheet
```

This project uses a **verified 400-task subset**: every task was checked
golden-vs-golden before inclusion (394/394 pass; init-vs-golden disagreement
0.3%). Tasks whose grader could not validate are excluded via an `exclude` key.

## OfficeQA

239 scored questions over 285 US Treasury Bulletins (~146 MB of text), from
`databricks/officeqa`.

**Gated.** Before the fetch will work, someone must open
<https://huggingface.co/datasets/databricks/officeqa> and accept the terms with
the same account whose token is in `HF_TOKEN`. Once, per account.

```bash
export HF_TOKEN=hf_...
./00_setup/02_benchmark_data.sh officeqa
```

Four bulletins changed upstream after the manifest was written; the 7 questions
grounded on them are excluded, leaving 239 of 246. `--include-tainted` restores
them, for checking only.

---

## Model weights

Not redistributed either — pulled from Hugging Face by
`00_setup/03_model_weights.sh`. Qwen3-8B ≈ 16 GB, Qwen3-14B ≈ 28 GB,
Qwen3.6-27B ≈ 60 GB. Point `HF_HOME` at an existing cache to avoid
re-downloading.

## What this repository *does* contain

The skills themselves (`skills/*.md`) are original to this project, as is all
code under `src/`, every runner script, and the `pools/` neutral-task file used
for vector extraction.

No licence has been chosen yet, so default copyright applies: this material may
not be reused without permission. Add a `LICENSE` file before sharing the
repository with anyone who needs to build on it — collaborators invited to a
private repo are still bound by default copyright.
