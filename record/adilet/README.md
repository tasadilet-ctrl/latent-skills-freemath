# Adilet's runs: text skills on math benchmarks without answer-format shortcuts

Status 2026-10-23. Box: 2 × RTX PRO 6000 Blackwell, vLLM 0.32, greedy, thinking off.
Some stages are still running; this file says which numbers are final and which are not.

## The question

On LiveMath every skill gain came from an answer-format shortcut: the meta-option
"One of the remaining options is correct, but a stronger result can be proven" is
correct 263/263 times (`../../skill_search/PROTOCOL.md`). Does any skill help when
there is no such shortcut? Two families were tried:

* **free-form** (no options at all): BeyondAIME, HARDMath2, RealMath. Still queued:
  IMO-AnswerBench, and ArxivMath with a Qwen3-14B target.
* **MCQ without a meta-option**, audited with no model first (`../../skill_search/mcq_math/audit_mcq.py`):
  MMLU-Pro math (TheoremQA + SciBench; centroid shortcut 11.6% against 10% chance)
  and SuperGPQA hard math (centroid 18.0%, so it is reported split by centroid).

Pipelines: `../../skill_search/skillopt_local/freemath/`, `../../skill_search/skillopt_local/mcqmath/`
(SkillOpt envs + launchers), `../../skill_search/mcq_math/` (kit-prompt runner, PROTOCOL.md selection).

## Results so far

**1. Transfer of the LiveMath skills to clean MCQ (Qwen3-8B, kit prompt + forcing, 2048 tokens; final).**
`reports/mcq_transfer_kit_stack_qwen3-8b.txt`. No skill beats no-system-prompt; the
length-matched placebos *hurt* (MMLU-Pro 72.7 → 64.0, SuperGPQA 34.8 → 28.0): they halve
reply length. "livemath_ts beats its placebo" holds only because that placebo is harmful.

**2. SkillOpt on free-form math (Qwen3-8B target, forced final eval; final).**
`reports/freemath_forced_qwen3-8b.txt`. Nothing significant anywhere.

| test | none | placebo | strength_audit | SkillOpt skill | SkillOpt kept |
|---|---|---|---|---|---|
| BeyondAIME (40) | 7.5 | 2.5 | 5.0 | 15.0 (p=0.38) | seed (0 of 4 accepted) |
| HARDMath2 (121) | 5.8 | 8.3 | 10.7 (p=0.11) | 8.3 | step 2 |
| RealMath (287) | 17.1 | 17.8 | 15.7 | 17.1 (+12/−12) | step 1 |

**3. SkillOpt on clean MCQ, SkillOpt's own stack (Qwen3-8B, 4096 tokens; final).**
`reports/mcqmath_skillopt_stack_qwen3-8b.txt`.
MMLU-Pro: learned skill 74.0 vs none 72.9 (p=0.67). SuperGPQA: **every** system prompt
is significantly worse than none (39.7), the learned skill too (32.5, p=0.005).
SkillOpt measures progress against its *seed*, never against no skill; on SuperGPQA the
seed itself costs ~10 points, so "+2 over the seed" was still −7 against nothing.

**4. PROTOCOL.md stage on the MCQ runs.** SkillOpt is only the draft generator; drafts
are chosen on dev by the mean gain over Qwen3-8B / 14B / 3.6-27B, with the centroid
disqualification rule and ties to the shorter skill (`protocol/*/selection*.txt`).

* MMLU-Pro (final, `protocol/mmlupro_math_tq_sb/report_rescored.txt`): no draft beats
  no skill on dev; the protocol picks the seed (+ empty tags, −1.0). On test that
  4-line seed is 73.4 vs 72.9 (8B, n.s.), **81.1 vs 75.6 (14B, p=0.006)**, **91.0 vs 93.4
  (27B, p=0.012)**: opposite signs on two models, and the 14B lost 2 points on dev with
  the same draft. Read as model-specific and unreplicated, not as a skill effect (~60
  comparisons in the table).
* SuperGPQA: dev selection done, chosen = the seed itself (+0.33); **test still running**.

## Things that went wrong, and are fixed

* **math-verify in threads**: its timeouts use `signal.alarm()`, so inside SkillOpt's
  rollout threads every symbolic/numeric check failed silently. Fixed with a process
  pool; runs scored before the fix were redone.
* **Format clash in the protocol stage**: SkillOpt skills say "answer as `<answer>X</answer>`",
  the kit prompt says "`Answer: <letter>`", and the model writes hybrids
  (`Answer: <answer>G</answer>`). The strict parser read none of them and cost drafts up
  to ~13 dev points. The parser (`mcq_math/evaluate_vllm_mcq.py`) now reads every committed
  form; all protocol results were re-scored from saved replies (`results_rescored`).
* **GPU 0 produced garbage silently after a reboot** (64/64 `locklocklock…`, no error).
  Two SkillOpt steps were rolled back and redone on GPU 1; the user reset the card.
  `orchestration/gpu_garbage_probe.py` is the 2-minute check.
* **A cut-off rescore** (reboot) replaced a full result file with 162 of 287 rows;
  `analyze_freemath.py` now uses a rescored file only when it is complete.
* Reboots kill tmux: launchers skip training only when `summary.json` exists, and
  SkillOpt resumes from `runtime_state.json`.

## What is in this folder

| path | contents |
|---|---|
| `reports/` | the final tables quoted above |
| `skills_learned/<run>/` | every SkillOpt skill version, `best_skill.md`, `summary.json`, `history.json` (no transcripts: they contain benchmark text) |
| `protocol/<bench>/` | PROTOCOL.md drafts' selection (original and re-scored), chosen skill, test report |
| `orchestration/` | the box scripts that chained the runs, and the GPU garbage probe |
| `make_table.py`, `latent_skills_table_updated.png` | the LiveMath table from earlier |

Still to come: SuperGPQA protocol test; SkillOpt on IMO-AnswerBench (8B) and ArxivMath
(14B target); the PROTOCOL.md stage on all five free-form benchmarks.
