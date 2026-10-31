# Alternatives to SkillOpt: literature notes (2026-10-31)

## What other pipelines report

| Pipeline | What it does | Evidence under controls |
|---|---|---|
| SkillOpt (2605.23904) | optimizer LLM edits one .md skill, accept only if held-out score improves | self-reported 52/52 wins; independent test on real repo tasks: +0.1 pt (2609.12742) |
| GEPA (2507.19457, ICLR 2026) | reflective rewrite of whole instructions, Pareto-frontier selection | paper: +12 on AIME-2025 vs MIPROv2, beats GRPO on Qwen3-8B; independent test: +4.9 pt but not separable from run-to-run noise (2609.12742) |
| SSO, self-supervised skill optimization (2607.28777) | probe skills from unlabeled runs, LLM judge, behavior extractor, rank behaviors, rewrite | close to GT-based optimizers; no placebo/length control reported |
| SkillLift (2609.15396) | learned rubric as cheap surrogate, re-aligned with few oracle rollouts | beats auto-skill methods at 40–70% less cost; no overfitting control reported |
| Matched-group skill validation (2606.08755) | keep a skill only if skill-augmented rollouts beat base rollouts on the same task | frontier-LLM skills have "highly mixed utility" |
| SkillX, SkillMaster, SkillRevise, Trace2Skill | library building / RL-managed skill banks / trace-based revision | agent benchmarks (ALFWorld, WebShop); no length-matched controls |

## Controlled studies (all agree with our math result)

* Signal or Noise? (2608.23067): 31 public web-dev skills, 4 models: skills **lower** Pass@2 by 1.3–4.2; a
  length-matched irrelevant skill reproduces most of the loss for some models. Recommends length-matched
  controls as a basic requirement.
* SkillCenter (2607.07676): retrieved skills never beat a length-matched placebo.
* When Skills Don't Help (2605.20023): +8.9 pt, CI [−6.8, +24.6], not significant.
* Skill Issue (2609.12742): see table.

Conclusion: no pipeline has a gain that survives a placebo control on tasks the model can already do.
Changing the optimizer will not fix our problem; the task choice is the problem.

## Plan: optimizer-found skills on generated, checkable tasks

1. Tasks: Reasoning Gym (2505.24760, open source, 100+ generators with exact checkers and difficulty
   knobs). Keep tasks where Qwen3-8B/14B score 10–60% without a skill and a known procedure exists
   (arithmetic/base conversion, counting, calendar, graph shortest path, sorting, cryptarithm, matrix ops).
2. Optimizer: GEPA (best independent result) with SkillOpt as a second arm; train on seeds A, select on
   seeds B, test once on seeds C. Fresh instances mean the skill cannot hold answers.
3. Anti-cheating checks (pre-registered):
   * beat placebo_notation and brevity_control, exact McNemar + Holm;
   * harder-difficulty test split than training (procedure must generalize);
   * skill text scanned for literal instances/answers;
   * trace check: replies must follow the skill's steps (as in positive_control);
   * flip analysis: skill-skill agreement must exceed skill-placebo agreement.
4. Vector arm on every skill that passes, as in positive_control.
