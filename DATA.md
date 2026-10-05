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

608 research-level mathematics questions, 5-way multiple choice, across 8
monthly releases (202511–202606).

**Public and ungated** — `LiveMathematicianBench/LiveMathematicianBench` on
Hugging Face. No token needed.

```bash
./00_setup/02_benchmark_data.sh livemath
```

The months are pinned to the 8 the reported cells used. It is a *live*
benchmark: each month adds questions from arXiv papers published after the
models' training cutoffs, which is what makes it contamination-resistant — and
also why the set must be pinned, or a re-run silently evaluates on more data
than the published numbers did.

The preparation step is not cosmetic. In the raw files the correct choice is
labelled `A` in **all 608 questions** — the letters encode canonical roles
(A = correct, C = weaker-true, D = wildcard trap), not a presentation order.
Served unshuffled, "always answer A" scores 100%. `prepare_livemath.py` shuffles
with a per-question deterministic seed: reproducible across runs and conditions,
not guessable. A correct build shows answers spread over A–E and a baseline near
20% (chance), not near 100%.

## SpreadsheetBench

The upstream **Verified 400** release (December 2025) — 400 expert-annotated
spreadsheet-editing tasks with golden workbooks.

**Public and ungated** — `KAKA22/SpreadsheetBench` on Hugging Face, mirrored at
<https://github.com/RUCKBReasoning/SpreadsheetBench>. No token needed.

```bash
./00_setup/02_benchmark_data.sh spreadsheet
```

The tarball this project used is **byte-identical to the official release**
(sha256 `10ef893dd29cb13a…`, 14 958 255 bytes) — there is no local modification.
Upstream ships 400 tasks and marks 2 as ungradeable (one whose input already
satisfies the answer, one whose golden workbook contradicts its own
instruction), so the **effective n is 398**.

`data/sb400_expected.json` records that shape and the script checks it after
unpacking. The point is not to patch anything — it is to notice if a future
re-download differs from what the reported cells ran against, since a changed
task count would move every SpreadsheetBench number with no error anywhere.

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
