# Latent Skills

**Does a procedural skill transfer better as a latent activation vector than as text in the prompt?**

This kit answers that question end to end: it turns a written skill into a steering
vector, checks the vector really *is* the skill, and measures both against three
benchmarks on three model sizes.

The answer it produced is negative, and that is the finding. See
[Results](#results) before you conclude the pipeline is broken.

---

## Contents

1. [Quick start](#quick-start)
2. [How it works](#how-it-works)
3. [The experiment matrix](#the-experiment-matrix)
4. [Running a benchmark](#running-a-benchmark)
5. [Making an embedding skill](#making-an-embedding-skill)
6. [Reading the results](#reading-the-results)
7. [The three traps](#the-three-traps)
8. [Results](#results)
9. [Configuration reference](#configuration-reference)
10. [Layout](#layout)
11. [Troubleshooting](#troubleshooting)

---

## Before you start: data and credentials

All three benchmarks **download**. The data is not redistributed here (answer
keys, and OfficeQA's licence forbids it), but `setup.sh` fetches everything:

| benchmark | source | credentials |
|---|---|---|
| LiveMath | `LiveMathematicianBench/LiveMathematicianBench` | **none** |
| SpreadsheetBench | `KAKA22/SpreadsheetBench` (Verified 400) | **none** |
| OfficeQA | `databricks/officeqa` | **a Hugging Face token** |

OfficeQA's document corpus is gated (`gated: auto` — approval is instant, but it
must be accepted once per account):

1. open <https://huggingface.co/datasets/databricks/officeqa> and accept the terms
2. `export HF_TOKEN=hf_...`

Without a token the other two still work; only OfficeQA is skipped.

Two more things to know:

- **vLLM is not in `requirements/`.** Both agent benchmarks need a served model:
  `.venv/bin/pip install vllm`.
- **`setup.sh` has not been verified end to end from a cold start.** The data
  fetchers and the `.agentvenv` / `.plotvenv` steps are tested; the torch
  environment has not been built by this script from scratch. Budget time for it
  to need fixing.

## Quick start

```bash
./setup.sh                                 # 30–60 min, mostly downloads
01_livemath_direct/run_baseline.sh
01_livemath_direct/run_text_skill.sh
06_reports/results_table.sh
```

`setup.sh` builds three Python environments, fetches the benchmark data and the
model weights, then runs a smoke test. It is safe to re-run — every step skips
what is already done.

On a cluster everything submits to SLURM automatically. On a workstation:

```bash
RUNNER=local GPU=0,1 01_livemath_direct/run_baseline.sh
```

---

## How it works

**A skill** is a markdown file — a written procedure, e.g. `skills/strength_audit.md`.
There is exactly **one canonical skill file per benchmark**; see
[Configuration](#configuration-reference).

**A text skill** is that file pasted in as the system prompt. The model always
has it and cannot fail to load it. It is deliberately *not* a file the agent
chooses to open: a progressive-disclosure skill would make a null result mean
"the agent never read it" rather than "the procedure did not help".

**An embedding skill** is a direction in the model's residual stream, built by
difference-in-means over a pool of neutral tasks, read at the final prompt token:

```
v = E[h_l | with skill] − E[h_l | without]
```

At inference it is added back, scaled relative to the activation norm:

```
h ← h + γ·‖h‖·v̂
```

**Fidelity** decides whether that vector actually *is* the skill:

```
fidelity = 1 − KL(text ‖ steered) / KL(text ‖ plain)
```

| value | meaning |
|---|---|
| 1.0 | steering reproduces the text skill exactly |
| 0.0 | steering achieves nothing the plain model did not already do |
| < 0 | steering moves *away* from the skill |

Benchmark accuracy cannot do this job. If a skill is worth two points on a
608-item 5-way choice, accuracy cannot separate "the vector works" from noise —
and picking the layer and γ by whichever accuracy came out highest is fitting the
test set.

---

## The experiment matrix

Per benchmark, per model:

| cell | what it is |
|---|---|
| **baseline** | no skill. The reference. |
| **text** | the skill as system prompt. The thing to beat. |
| **embed from placebo** | B1, **controlled**: `[placebo+skill] − [placebo]` |
| **embed from nothing** | B2, **uncontrolled**: `[skill] − [no system message]` |
| **CONTROL** | a vector built *from* the placebo. Contains no procedure. |

**B1 against B2 is the whole experiment.** B2's contrast carries the procedure
*and* the bare fact that instructional text sits in the system slot, with nothing
separating them. B1 cancels the second by putting length-matched filler on both
sides. The CONTROL closes it: a vector made from text with no procedure in it
should do nothing.

Reporting B2 alone as "the embedding skill works" is the easiest way to publish
something untrue from this pipeline.

> **Naming.** It is `from_placebo` / `from_nothing`, not `vs`. The placebo is
> what the vector was *extracted against* — the baseline of the contrast — not
> something the result is compared with.

---

## Running a benchmark

Each benchmark has its own folder, and **one script per cell**. Nothing does two
things.

### LiveMath — `01_livemath_direct/`
608 research-level maths questions, 5-way choice, chance = 20%. No tools. The
cleanest benchmark and the one every method decision was made on.

```bash
./run_baseline.sh
./run_text_skill.sh
./run_embed_from_placebo.sh   <vec> <layers> <gamma>
./run_embed_from_nothing.sh   <vec> <layers> <gamma>
./run_control_placebo_only.sh <vec> <layers> <gamma>
```

**Every benchmark folder has these same five scripts**, one per cell of the
matrix, so the matrix is complete everywhere rather than only on LiveMath.

For the two **agent** benchmarks there is no `--condition embed` flag: steering
comes from the *server*, and the adapter labels the cell from what `/health`
reports. So an embed script is the baseline command pointed at the hooked
server. Each one calls `require_steering` first, which refuses to run against a
plain server — otherwise the cell would quietly come out as a second baseline,
indistinguishable from a real one in the results.

### SpreadsheetBench — `02_spreadsheetbench_agent/` and `03_spreadsheetbench_single_turn/`
400 real spreadsheet-editing tasks. The agent arm gives the model a shell, a file
editor and a workspace holding `input.xlsx`; it must leave `output.xlsx` behind.

**The agent arm needs a served model** — it talks HTTP and loads no weights:

```bash
00_setup/05_serve_model.sh plain      # in another terminal or job
02_spreadsheetbench_agent/run_baseline.sh
```

The single-turn arm runs in-process with batching and needs no server. It exists
to make the embedding cell affordable: ~1 h, against ~25 h through the serial
hooked server the agent arm would require. It is a **separate row**, not a cheaper
version of the same cell — no tools means strictly lower scores.

### OfficeQA — `04_officeqa_agent/`
239 questions over 285 US Treasury Bulletins (~146 MB). Must be an agent
benchmark: the documents one question cites total ~215k tokens at the median and
1.2M at worst, so *zero* questions fit an 8B context. The agent greps the files
on disk instead.

---

## Making an embedding skill

`05_make_embedding_skills/`, in order:

```bash
./01_extract_from_placebo.sh            # B1, the controlled vector
./02_extract_from_nothing.sh            # B2, the uncontrolled vector
./03_extract_control_from_placebo.sh    # the null vector
./04_measure_fidelity.sh    <vec>       # which (layer, γ) reproduces the skill
./05_check_degeneration.sh  <vec>       # ...and does not wreck generation
./06_check_skill_compliance.sh          # optional: is the skill even followed?
```

Then take the chosen operating point to a benchmark:

```bash
01_livemath_direct/run_embed_from_placebo.sh \
    ../vectors/v_qwen3-8b_compare_claims_placebo.pt 34 0.3
```

**Step 05 is not optional.** Fidelity is measured teacher-forced — scored against
a reference continuation one token at a time. A vector can score well on fidelity
while free generation has collapsed into repetition. Step 05 sweeps the same grid
and reports a distinct-token ratio.

**Pick the best fidelity among settings that pass step 05**, not the best fidelity
overall.

---

## Reading the results

```bash
06_reports/results_table.sh     # per benchmark: accuracy, CI, McNemar
06_reports/full_matrix.sh       # every axis at once — read this one
06_reports/table_png.sh         # → results_table.png
```

Columns:

| column | meaning |
|---|---|
| `acc %` | exact-match. LiveMath chance is 20%. |
| `95% CI` | Wilson interval |
| `n` | **must** equal the full benchmark size (608 / 400 / 239) |
| `parse` | fraction of replies that committed to an answer; want 1.000 |
| `d vs base` | points against this model's own baseline |
| `McNemar p` | **paired** test — both conditions answer identical items |

McNemar is paired because an unpaired two-proportion test throws the pairing away
and needs a far larger effect to detect anything.

**Harness is a separate row, not a detail.** The agent benchmarks moved from
OpenHands to the Strands SDK on 2026-10-05. The two do not expose identical
tools, names or error text, so their cells are never merged. See `HARNESS_SWAP.txt`.

---

## The three traps

Each of these produced a wrong number with **no error in any log**.

### 1. Truncation — a score *below* chance
The 27B scored 16.94% on a 5-way choice where chance is 20%. Not a bad model:
51.6% of replies hit the 2048-token cap mid-deliberation and never emitted an
answer. Raising the cap to 4096 with an answer cue moved it to 33.06% — a
16-point correction that had looked like a finding.

→ **Check `parse_rate` is 1.000.** A score under chance means broken, not bad.
The 27B needs `MAXNEW=4096`.

### 2. Tool-call parser — a score of *exactly* 0%
vLLM needs `--tool-call-parser` matched to the model generation: Qwen3-8B/14B emit
Hermes JSON, Qwen3.6-27B emits `qwen3_xml`. Mismatch it and vLLM returns
`tool_calls: []`, the agent executes nothing, every task fails silently. Cost three
runs and two wrong conclusions.

→ `00_setup/05_serve_model.sh` picks it from `MODEL_ID`. **Confirm a real tool call
in the first episode log** before trusting an agent number.

### 3. Dead shard — a quietly incomplete cell
Four shards run per cell. A bare `wait` returns only the last one's status, so a
dead shard left `n=456` where 608 was expected and the cell still reported a
number. `lib/common.sh` now checks every PID and prints
`INCOMPLETE -- do not trust this cell`.

→ **Check `n`.**

A fourth, smaller one: result filenames are deterministic, so re-running a cell
**overwrites** it. Move `results/` aside first if you want to keep what is there.

---

## Results

From two complete 4-condition matrices on LiveMath:

> **What activation steering contributes tracks the presence of instructional text
> in the extraction contrast, not the procedural content of the skill.**

The uncontrolled arm (B2) carried most of the text skill's apparent effect.
Subtracting a length-matched placebo (B1) removed it. The CONTROL — a vector built
from placebo text containing no procedure — behaved like the real skill's vector.

Secondary: **fidelity does not predict effect.** The 14B's best vector scored
+0.638 fidelity and −0.16 accuracy, while its text skill gave +2.30. A vector can
faithfully reproduce a skill's output distribution and still be useless. Report both.

Six text cells, six nulls, five positive. Full tables in `RESULTS_TABLE.txt`.

This is a negative result. The pipeline is not broken — **do not tune it until the
embedding arm looks better.**

---

## Configuration reference

Everything is an environment variable, read by `env.sh`. Nothing needs editing to run.

| variable | default | what it does |
|---|---|---|
| `MODEL_ID` | `Qwen/Qwen3-8B` | which model; `MODEL_TAG` follows automatically |
| `RUNNER` | auto | `sbatch` or `local` |
| `GPU` | `0` | which GPUs `local` may use, e.g. `0,1` |
| `LIMIT` | `608` | questions per benchmark; lower to smoke-test |
| `BS` | `8` | batch size; lower if you run out of VRAM |
| `SHARDS` | `4` | parallel shards, one per GPU |
| `MAXNEW` | `2048` | generation cap. **The 27B needs 4096** |
| `SKILL_LIVEMATH` | `strength_audit.md` | the canonical LiveMath skill |
| `SKILL_SPREADSHEET` | `spreadsheet_edit.md` | |
| `SKILL_OFFICEQA` | `officeqa_lookup.md` | |
| `SKILL_PLACEBO` | `placebo_matched.md` | the length-matched control |
| `LLM_BASE_URL` | `http://127.0.0.1:9000` | where agent benchmarks find a model |
| `HF_HOME` | `$KIT/.hf_cache` | point at an existing cache to skip downloads |

**One skill file per benchmark, by design.** Three near-identical filenames in one
folder is how a run gets pointed at the wrong one — which fails silently and looks
like a result. LiveMath's skill was replaced on 2026-10-05: `strength_audit.md`
is canonical, and all three `compare_claims` drafts are in `skills/archive/`.
Their history, why the first one *hurt*, and the measured effect of the
replacement are in `skills/notes/README.md`.

---

## Layout

```
setup.sh                          run first; chains all of 00_setup/
env.sh                            every path and knob
lib/common.sh                     the submit helper — sbatch or local

00_setup/                         5 steps, each runnable on its own
01_livemath_direct/               5 cells   (no tools, no server)
02_spreadsheetbench_agent/        2 cells   (needs a served model)
03_spreadsheetbench_single_turn/  3 cells   (in-process, batched)
04_officeqa_agent/                2 cells   (needs a served model)
05_make_embedding_skills/         6 steps   ← the method
06_reports/                       3 views

src/        the python; nothing here needs editing to run
skills/     one .md per benchmark, plus the placebo controls
tests/      harness unit tests, no GPU needed
```

Every folder has a `README.txt` explaining its cells and what the comparison is
for. If you read only one, read `05_make_embedding_skills/README.txt`.

Each script carries its reasoning in the header — not just usage.

---

## Troubleshooting

**`FAILED: no eval environment at .../python`** — run `./setup.sh`.

**`FAILED: missing data: .../spreadsheetbench_verified_400`** — run
`00_setup/02_benchmark_data.sh`.

**`FAILED: nothing answering at http://127.0.0.1:9000`** — the agent benchmarks
need a served model: `00_setup/05_serve_model.sh plain`.

**OfficeQA fetch returns 401** — `databricks/officeqa` is gated. Accept the terms
on the dataset page with the account whose `HF_TOKEN` you are using, once.

**Jobs sit in `PD` for hours** — normal on a shared cluster. Do not "fix" it by
lowering `--gpus-per-node` or switching partition. Submit everything you can up
front; queue position is worth more than tidy sequencing.

**My numbers differ from the published ones** — decoding is greedy, so runs are
deterministic. Check `MODEL_ID`, `LIMIT`, and which skill file, in that order.

**Never edit a `.sh` while a job is executing it.** bash reads scripts
incrementally and will execute garbage. Python files are safe (read once at import).

**`g002` / `g006`** are excluded by default. g002's munge auth died 2026-08-14 and
SLURM still reports it IDLE; g006 runs jobs that hold GPU memory without requesting
it through gres.
