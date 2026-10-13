# LiveMath skill search — protocol (written 2026-10-12, before any run)

Goal: a text skill that improves LiveMath accuracy through mathematics, not
through the benchmark's answer format.

## Two known format crutches (measured with no model)

1. META: 263/608 questions contain the option "One of the remaining options is
   correct, but a stronger result can be proven". It is correct 263/263.
2. CENTROID: on the other 345 questions, picking the option whose text is most
   similar (difflib ratio, summed) to the other four scores **68.1%** — above
   every model's baseline (27B: 52.5%). Distractors are one-edit perturbations
   of the true theorem, so the true statement sits at the centre.

A skill must not mention either. Neither may be used to pick between drafts.

## Split (skill_search/split.json, deterministic hash of the id)

* dev   123 OTHER questions — drafts are compared here, and only here.
* test  222 OTHER questions — touched once, by the chosen skill.
* meta  263 META questions  — never used for selection; reported only.

Each id also carries `centroid_right` (does the similarity shortcut get it right).

## Selection rule (fixed in advance)

Among drafts, choose the one with the highest mean dev-OTHER accuracy gain over
baseline, averaged over the three models. A draft is disqualified if its mean
gain on the centroid-WRONG dev questions is more than 3 points below its gain
on centroid-right ones AND its overall dev gain comes only from centroid-right
items (that pattern = learning the shortcut, not the maths). Ties -> shorter skill.

## Final report

On test-OTHER (222) and the full 608: baseline, placebo_matched, strength_audit,
strength_audit_nometa, chosen skill; split META / OTHER / OTHER-centroid-wrong;
paired exact McNemar vs baseline. Same vLLM stack for every cell (greedy,
enable_thinking=False, kit prompt + answer forcing, max_new 2048 / 4096 for 27B).
