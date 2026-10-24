# Adilet's runs: text skills on math benchmarks without answer-format shortcuts

Status 2026-10-24: **all stages finished.** Box: 2 × RTX PRO 6000 Blackwell, vLLM 0.32,
greedy, thinking off. The summary table is `math_skills_table.png`
(`make_math_skills_table.py`, cells in `math_skills_cells.json`, computed from the saved
per-question results).

![summary](math_skills_table.png)

## Main conclusion

**No text skill beats giving the model no system prompt**, on 7 math benchmarks that
have no answer-format shortcut, for Qwen3-8B, Qwen3-14B and Qwen3.6-27B, with
PROTOCOL.md's selection rule. 10 of the table's 96 comparisons are significant
(p<0.05, uncorrected; ~5 are expected by chance): **9 are losses**, and the one gain
(MMLU-Pro 14B, +5.5) reverses on the 27B (−2.5, also significant) with the same text and
did not show on dev. What notes change is mostly **how long the model reasons**: the
length-matched placebos halve reply length and are the most common significant losses.

The LiveMath result this started from was a loophole: there, every skill gain came from
the meta-option "One of the remaining options is correct, but a stronger result can be
proven", correct 263/263 times (`../../skill_search/PROTOCOL.md`).

Not covered: other model families, thinking mode, optimizers stronger than
Qwen3.6-27B (the SkillOpt paper used GPT-5.5), and **vector/embedding skills**: none were
run on these benchmarks (the vector results in `../` are Adil's LiveMath runs).

## The benchmarks

* **MCQ without a meta-option**, audited with no model first (`../../skill_search/mcq_math/audit_mcq.py`):
  MMLU-Pro math (TheoremQA + SciBench; centroid shortcut 11.6% against 10% chance) and
  SuperGPQA hard math (centroid 18.0%, so reported split by centroid).
* **Free-form** (no options): BeyondAIME, HARDMath2, RealMath, IMO-AnswerBench,
  ArxivMath (SkillOpt target Qwen3-14B; 8B was at the floor).

Pipelines: `../../skill_search/skillopt_local/freemath/` and `.../mcqmath/` (SkillOpt envs
and launchers), `../../skill_search/mcq_math/` (kit-prompt runners, PROTOCOL.md selection).

## Results, in the order they were produced

**1. LiveMath skills transferred to clean MCQ** (8B, kit prompt + forcing, 2048 tokens).
`reports/mcq_transfer_kit_stack_qwen3-8b.txt`. No skill beats no-system-prompt; the
placebos hurt (MMLU-Pro 72.7 → 64.0, SuperGPQA 34.8 → 28.0) by halving reply length.
"livemath_ts beats its placebo" holds only because that placebo is harmful.

**2. SkillOpt, 8B target, SkillOpt's own stack.** `reports/freemath_forced_qwen3-8b.txt`,
`reports/mcqmath_skillopt_stack_qwen3-8b.txt`. Val gains did not reach test. SkillOpt
measures progress against its *seed*, never against no skill: on SuperGPQA the seed
itself costs ~10 points, so "+2 over the seed" was still −7 against nothing.

**3. PROTOCOL.md stage (the table).** SkillOpt is only the draft generator. Drafts are
chosen on dev by the mean gain over the three models (centroid disqualification for MCQ;
ties to the shorter skill), then the test split is evaluated once, with the kit's prompt
and forcing (2048 tokens, 4096 for the 27B).
`protocol/<mcq bench>/report_rescored.txt`, `protocol_fm/<bench>/report.txt`, and the
selections next to them. **On all 7 benchmarks the chosen draft is SkillOpt's 4-line
seed, or the seed plus empty tags**: every longer, optimized draft lost on dev.

## Skill audit: do any skills exploit the benchmark format?

| skill | format-exploiting content | effect |
|---|---|---|
| strength_audit | **yes**: step 5, the meta-option rule | its whole LiveMath gain; nothing elsewhere |
| strength_audit_nometa | no | flat |
| livemath_ts | partly: says "the wrong ones usually differ from the right one in a single detail" (the basis of the centroid shortcut), never says to use it | none: on LiveMath its gain was larger where the centroid is *wrong* (+8.0 vs +6.3), and its placebo matched it |
| placebos | no procedure; "don't pad" shortens replies | they hurt; a length effect |
| SkillOpt MCQ skills | mostly method; two **memorized training items** (the ∛130 answer key `5.06577778`, Fermat primes for a polygon question, both in the train split) and one guessing rule ("pick the option with the same structure as your result") | no gain on centroid-right items; neither memorizing version was chosen |
| SkillOpt free-form skills | method plus **benchmark-construction priors** (HARDMath2 "reject constant answers", "amplitude is ALWAYS Q^(−1/4)"; RealMath "never answer 'cannot be determined'"), anti-loop rules | none significant |
| SkillOpt LiveMath skill (Adil) | **yes**: "Meta-Option Absolute Priority" | the LiveMath gain |

## Things that went wrong, and are fixed

* **math-verify in threads**: its timeouts use `signal.alarm()`, so inside SkillOpt's
  rollout threads every symbolic/numeric check failed silently. Fixed with a process
  pool; runs scored before the fix were redone.
* **Format clash**: SkillOpt skills say "answer as `<answer>X</answer>`", the kit prompt
  says "`Answer: <letter>`", and the model writes hybrids (`Answer: <answer>G</answer>`).
  The strict parser read none of them. `mcq_math/evaluate_vllm_mcq.py` now reads every
  committed form; all protocol results were re-scored from saved replies.
* **GPU 0 produced garbage silently after a reboot** (64/64 `locklocklock…`, no error):
  two SkillOpt steps were rolled back and redone; the card was reset.
  `orchestration/gpu_garbage_probe.py` is the 2-minute check.
* **Another user's training grew into our card mid-cell** and OOM-killed an 8B cell; the
  protocol stage now waits for an idle GPU (the kit's < 2 GB rule).
* **A cut-off rescore** (reboot) replaced a full result file with 162 of 287 rows;
  `analyze_freemath.py` now uses a rescored file only when it is complete.
* Reboots kill tmux: launchers skip training only when `summary.json` exists, and
  SkillOpt resumes from `runtime_state.json`.

## What is in this folder

| path | contents |
|---|---|
| `math_skills_table.png` + script + cells | the summary table above |
| `reports/` | results 1 and 2 |
| `protocol/<mcq bench>/`, `protocol_fm/<bench>/` | PROTOCOL.md selection (dev), chosen draft, test report |
| `skills_learned/<run>/` | every SkillOpt skill version, `best_skill.md`, `summary.json`, `history.json` (no transcripts: they contain benchmark text) |
| `orchestration/` | the box scripts that chained the runs, and the GPU garbage probe |
| `make_table.py`, `latent_skills_table_updated.png` | the earlier LiveMath table |
