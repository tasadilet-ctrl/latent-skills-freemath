# Making a text skill with SkillOpt, on local models

This folder runs [SkillOpt](https://github.com/microsoft/SkillOpt) (Microsoft, MIT
licence; paper: [arXiv:2605.23904](https://arxiv.org/abs/2605.23904)) on our cluster
with two local Qwen models instead of GPT-5.5. You give it a benchmark split and a
target model; it gives you back a skill file (`best_skill.md`) that you can drop into
`skills/` and evaluate with the rest of the kit, as text or as a steering vector.

We have run it end to end on LiveMath (Qwen3-8B target). SkillOpt also ships
OfficeQA and SpreadsheetBench environments, and a template for new benchmarks;
those have **not** been run here yet (section 7).

**Read section 9 before trusting a result.** On LiveMath, SkillOpt's whole gain
came from a benchmark artefact, not from better maths.

Contents:
1. What SkillOpt does, step by step
2. What you need
3. Install
4. Make the data split
5. Launch a run
6. Read the output
7. Use the skill in the kit
8. A new benchmark
9. Pitfalls (read this)
10. Files in this folder

---

## 1. What SkillOpt does, step by step

A *skill* is a markdown document that goes into the target model's system prompt.
SkillOpt treats that document like the weights of a network and "trains" it with a
second model, the *optimizer*, which reads the target's mistakes and edits the
document. Nothing is fine-tuned; only the text changes.

Two models:

* **target**: the model the skill is for. It answers the benchmark questions
  with the current skill in its system prompt. Here: Qwen3-8B, thinking off,
  temperature 0.
* **optimizer**: reads the target's transcripts and writes the edits. Here:
  Qwen3.6-27B with thinking on (SkillOpt's paper uses GPT-5.5).

Three splits, used for different things:

* **train**: the target answers these and the optimizer learns from the results.
* **val** (SkillOpt calls it "selection"): decides whether an edited skill is kept.
* **test**: scored once at the start (no skill) and once at the end (best skill).
  Never seen by the optimizer.

It starts from a seed skill (`skillopt/envs/<benchmark>/skills/initial.md` in the
SkillOpt checkout, a few generic lines). Then, for each epoch and each step
within it:

1. **Rollout.** The target answers a batch of training questions
   (`train.batch_size`, default 40) with the current skill. Each answer gets a
   `hard` score (0/1) and a `soft` score (0 to 1). The transcript of every
   question is saved.
2. **Reflect.** The optimizer reads the transcripts in minibatches of
   `gradient.minibatch_size` (default 8), failures and successes alike, and
   proposes *edit patches*: "add this rule", "change this sentence", each with
   a reason. This is the "backward pass".
3. **Aggregate.** Patches that say the same thing are merged
   (`gradient.merge_batch_size`).
4. **Select.** The optimizer ranks the merged patches. Only the top
   `optimizer.learning_rate` of them (default 4) are applied, decaying to
   `min_learning_rate` (2) on a cosine schedule. This is the "learning rate":
   how many edits one step may make.
5. **Update.** The selected patches are applied to the skill
   (`optimizer.skill_update_mode: patch`), giving a candidate skill.
6. **Gate.** The target answers the whole val split with the candidate. The
   candidate replaces the current skill only if its val score is **strictly
   higher**. Otherwise it is thrown away and the old skill stays.

At the end of each epoch, from epoch 2 on:

* **Slow update**: the previous epoch's skill and the current one both answer
  the same `slow_update_samples` (20) training questions. The optimizer looks at
  what improved, what regressed and what keeps failing, and writes higher-level
  guidance into a protected block of the skill (between `<!-- SLOW_UPDATE_START -->`
  and `<!-- SLOW_UPDATE_END -->`). This counters forgetting.
* **Meta skill**: the optimizer writes a short memory of which strategies worked,
  and that memory is fed back into later reflect/update calls.

After `train.num_epochs` (default 4) epochs, the skill with the best val score is
`best_skill.md`, and it is scored on test.

Number of steps = epochs × ceil(train size / batch size). With LiveMath's 35
training questions and batch 40 that is one step per epoch, 4 steps in all.

SkillOpt's own docs, worth reading once: `docs/guide/training-loop.md`,
`docs/guide/configuration.md` and `docs/guide/new-benchmark.md` in the checkout.

## 2. What you need

* 2 GPUs on one node (H100 80 GB here): GPU0 serves the target, GPU1 the optimizer.
  A 27B optimizer with 131k context needs the whole card.
* A Python env with vLLM and the models already downloaded. On this cluster that
  is `~adil.taibassarov/qwen_vllm_scripts_bundle_20260602` (its `.venv` and
  `hf_cache`). Point `VLLM_ENV` at your own copy if you have one; the jobs run
  with `HF_HUB_OFFLINE=1`, so the models must already be in `$VLLM_ENV/hf_cache`.
* [uv](https://docs.astral.sh/uv/) for SkillOpt's own venv.
* The benchmark data, split into train/val/test (section 4).

## 3. Install

```bash
skill_search/skillopt_local/setup.sh            # -> ~/skillopt_work/SkillOpt
# or: setup.sh /some/other/work/dir   (then export SKILLOPT_WORK=/some/other/work/dir)
```

This clones SkillOpt, checks out commit `343db22` (the one all our runs used),
makes `.venv` with Python 3.12, and installs SkillOpt plus `json_repair`.
`json_repair` is needed because a local optimizer's JSON is not always clean.
SkillOpt itself is used unmodified.

## 4. Make the data split

SkillOpt reads `<split dir>/{train,val,test}/` in each benchmark loader's own format.

**LiveMath** (SkillOpt's published 35/17/125 split, same question IDs as the paper):

```bash
W=~/skillopt_work
for m in 202511 202512 202601 202602; do
  mkdir -p $W/lm_raw/$m && cp data/lm_$m.json $W/lm_raw/$m/qa_${m}_final.json
done
cd $W/SkillOpt && .venv/bin/python ~/latent-skills-kit/skill_search/skillopt_local/make_split.py $W
#   -> $W/lm_split/{train,val,test}/items.json   (prints: train 35, val 17, test 125)
```

`make_split.py` uses SkillOpt's ID lists (`data/livemathematicianbench_id_split/`)
rather than its ratio mode, because at this commit the ratio mode gives 35/18/124.

**OfficeQA, SpreadsheetBench**: SkillOpt ships ID splits in
`data/officeqa_id_split/` and `data/spreadsheetbench_id_split/`, and loaders in
`skillopt/envs/<name>/dataloader.py`. Read the loader to see which fields and file
layout it expects, then write a small script like `make_split.py` that writes our
copy of the data in that layout. The data is gated: do not commit it.

**Any benchmark**: keep the val split large enough to tell skills apart.
The gate compares val scores, so with 17 questions one question is 6 points.

## 5. Launch a run

```bash
cd ~/latent-skills-kit/skill_search/skillopt_local
sbatch -J lm_qwen3-8b --output=$HOME/skillopt_work/logs/%x_%j.out run_skillopt.sbatch \
    configs/livemathematicianbench/default.yaml Qwen/Qwen3-8B ~/skillopt_work/lm_split
```

Arguments: SkillOpt config (relative to the checkout), target model (HF id, must be
in the cache), split dir. Anything after that goes to SkillOpt's `--cfg-options`,
for example `train.num_epochs=2 train.batch_size=20`.

What the job does:

1. Starts vLLM for the target on GPU0 (context `TARGET_MAX_LEN`, default 24576;
   raise it for long inputs such as OfficeQA pages).
2. Starts vLLM for the optimizer on GPU1: 131k context, `--max-num-seqs 32`,
   and `--reasoning-parser qwen3`, so its thinking is kept out of the JSON it returns.
3. Waits until both answer `/health` (up to 20 min).
4. Runs `scripts/train.py` with the `qwen_chat` backend for both roles. Target
   thinking is off and optimizer thinking is on, passed as `--cfg-options`.
5. Kills both servers when training ends.

Our LiveMath run took 3.0 h of wall time (10,759 s) for 4 steps. Most of the
time goes to reflection and aggregation by the 27B optimizer, and it used 2.36M
tokens in total. The 12 h limit leaves room for bigger train splits.

Monitoring:

* `$SKILLOPT_WORK/logs/<name>_<jobid>.out`: SkillOpt's progress.
* `$SKILLOPT_WORK/logs/<name>_target_*.log`, `<name>_optimizer_*.log`: the vLLM servers.
  Look here if the job dies before "servers up".
* `$SKILLOPT_WORK/outputs/<name>/steps/`: one folder per step as it completes.

## 6. Read the output

`$SKILLOPT_WORK/outputs/<name>/` (our LiveMath run is copied to
`run_qwen3-8b_default/` here, without the per-question transcripts, which contain
benchmark text):

| file | what it is |
|---|---|
| `best_skill.md` | **the result**: the skill with the best val score |
| `skills/skill_v000N.md` | the skill after each accepted step (v0000 = the seed) |
| `summary.json` | `baseline_test_hard` vs `test_hard` (test accuracy without / with the skill), val scores, accepts/rejects, wall time, tokens |
| `history.json` | per step: timing per stage, tokens per stage, rollout score, val score |
| `test_eval_baseline/`, `test_eval/` | test accuracy per task type, without / with the skill |
| `steps/`, `slow_update/`, `meta_skill/` | the optimizer's patches, rankings and notes, step by step |

Quick look:

```bash
python3 -c "import json; s=json.load(open('summary.json')); print({k: s[k] for k in ('baseline_test_hard','test_hard','baseline_selection_hard','best_selection_hard','total_accepts','total_rejects','total_wall_time_s')})"
```

Then **read `best_skill.md` line by line** (section 9 says why). Diffing
consecutive `skills/skill_v000N.md` files shows which edit each step made.

## 7. Use the skill in the kit

1. Copy it in: `cp $SKILLOPT_WORK/outputs/<name>/best_skill.md skills/<benchmark>_skillopt_<model>.md`.
   Keep the `SLOW_UPDATE` block: it is part of what was optimized.
   (Our LiveMath one is `skills/skillopt/skillopt_qwen3-8b_learned.md`.)
2. Score it **only on questions SkillOpt never trained or gated on**. For LiveMath,
   the 52 train+val IDs are in `skill_search/ids_skillopt_trainval.json`, and every
   table in `skills/README.md` scores the other 556.
3. Text arm, fast (vLLM):
   `MODEL_ID=Qwen/Qwen3-8B python src/evaluate_vllm.py --skills none skills/<file>.md --max-new-tokens 2048 --out-dir results_vllm/<folder>`
4. Make a length-matched placebo (same length, no procedure; see
   `skills/placebo_*.md`) and run it next to the skill. Without it you cannot tell
   "this skill helps" from "any system prompt helps".
5. As a steering vector, same as every other skill:
   `python src/extract_vectors.py --pool neutral --n 50 --skill skills/<file>.md [--baseline-skill skills/<placebo>.md] --out vectors/...`,
   then `src/evaluate.py --condition embed`. Rakhat's recipes need replies on
   training questions: `src/rakhat_vectors.py`.
6. If the benchmark has a known shortcut, split the score by it, as LiveMath's
   META/OTHER split does (`skill_search/skillopt/analyze.py`).

## 8. A new benchmark

SkillOpt needs four pieces. Its template is `skillopt/envs/_template/` and its
guide is `docs/guide/new-benchmark.md`. The OfficeQA env (`skillopt/envs/officeqa/`)
is the cleanest working example to copy.

1. **Loader** (`dataloader.py`): subclass `SplitDataLoader` and implement
   `load_split_items(split_path)`, returning a list of dicts that each have an
   `id` plus whatever fields your rollout needs (question, ground truth, and a
   `task_type` if you want per-type results).
2. **Rollout** (in `adapter.py`): for a batch of items, build the target prompt
   with the current skill as system prompt, call the target, and score the reply.
   For each item return `{"id": str, "hard": 0 or 1, "soft": float in [0, 1]}`, and
   write the conversation to `<out_dir>/predictions/<id>/conversation.json`.
   The inherited `reflect()` reads those files, so without them the optimizer sees
   nothing. Reuse the kit's scorer if we already have one (for example
   `src/evaluate.py`'s `score_*` functions or `src/run_oqa_agent.grade`), so that
   SkillOpt optimizes the same metric we report.
3. **Adapter** (`adapter.py`): subclass `EnvAdapter`, wire in the loader and
   rollout (`build_*_env`, `rollout`, `get_task_types`), and leave `reflect` inherited.
4. **Config** (`configs/<name>/default.yaml`): copy `config_template.yaml` and set
   `_base_: ../_base_/default.yaml` (a string, not a list), `env.name`,
   `env.skill_init` (a seed skill: a title and two or three generic lines are enough),
   `env.max_completion_tokens` and `env.workers`.
5. **Register** it: add a `try/except ImportError` block mapping your env name to
   the adapter in `_register_builtins()` in **both** `scripts/train.py` and
   `scripts/eval_only.py`.

That means editing the SkillOpt checkout. Keep those changes in a branch of your
own fork, or as a patch file in this folder, and say which in your PR, so others
can reproduce the run.

Before a full run, do a cheap smoke run:
`train.num_epochs=1 train.batch_size=8 env.limit=16` (check that your loader honours `env.limit`). It checks the plumbing in
minutes instead of hours.

## 9. Pitfalls (read this)

**The optimizer finds shortcuts.** It edits the skill toward whatever raises the
val score, including artefacts of the benchmark. On LiveMath, 263 of 608 questions
contain the option "One of the remaining options is correct, but a stronger result
can be proven", and it is correct every time. Our run wrote this into the skill as
"Meta-Option Absolute Priority: ... it IS the correct answer". Test accuracy went
21.6 → 56.0, but on the questions without that option it went *down*, 36.6 → 28.2.
SkillOpt's released GPT-5.5 skill shows the same pattern. So:

* read the learned skill and look for rules that are about the benchmark rather
  than the task (answer positions, recurring phrasings, formats);
* split test accuracy by any such artefact you find;
* compare against a placebo of the same length;
* report the split, not just the headline number.

**Config beats environment.** The `qwen_chat` thinking mode set in the config
overrides `*_QWEN_CHAT_THINKING_MODE` env vars, so pass it with `--cfg-options`
(the launcher does).

**The optimizer's thinking must be parsed out.** Without `--reasoning-parser qwen3`
on the optimizer server, its patches arrive wrapped in thinking text and fail to
parse. Even with it, keep `json_repair` installed.

**Context lengths.** The optimizer prompt holds a minibatch of full transcripts:
131k context, and `--max-num-seqs 32` so the KV cache fits. If target replies are
long (OfficeQA pages, long proofs), raise `TARGET_MAX_LEN` and consider
`gradient.minibatch_size=4`.

**Small val splits make the gate noisy.** With 17 val questions, one lucky
question can decide whether an edit is kept. All four steps of our run were
accepted. Use a bigger val split if the benchmark allows it.

**Cluster.** The QOS allows 8 GPUs per user and this job takes 2. Nodes g002 and
g006 are excluded (broken), and so is g004 (about 10× slower).
`ninja` must be on `PATH` for vLLM's torch.compile; the launcher adds the vLLM env's `bin`.

**Different optimizer, different skill.** Qwen3.6-27B is a weaker optimizer than
the GPT-5.5 in the paper. Expect a different skill, not necessarily a worse score.

## 10. Files in this folder

| file | what it is |
|---|---|
| `setup.sh` | clone and install SkillOpt at the pinned commit |
| `run_skillopt.sbatch` | the SLURM job: two vLLM servers + `train.py` |
| `make_split.py` | LiveMath split in SkillOpt's format (their published IDs) |
| `run_qwen3-8b_default/` | our LiveMath run: best skill, every accepted version, summary, history, test summaries |
