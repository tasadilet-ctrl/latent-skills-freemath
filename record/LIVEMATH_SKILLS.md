# LiveMath: strength_audit, its no-meta ablation, and a crutch-free skill search

## What LiveMath rewards besides maths
* META: 263/608 questions offer "One of the remaining options is correct, but a
  stronger result can be proven". It is the correct answer in 263/263 cases.
* CENTROID: on the other 345, distractors are one-edit tweaks of the true
  theorem, so picking the option most textually similar to the other four
  scores 68.1% with no model (above every model's baseline).

## Skills
* skills/strength_audit.md        -- Adilet's skill (names the meta option).
* skills/strength_audit_nometa.md -- identical minus the meta-option step.
* skills/search/*.md              -- drafts written to avoid both crutches;
  proof_sketch.md was selected (skill_search/PROTOCOL.md, fixed before running).

## Results and figures
* record/results/livemath_*_s?of2.json  -- transformers runs, baseline /
  text_strength_audit / text_strength_audit_nometa, full 608.
  Figure: record/tables/results_table_meta_split.png, livemath_meta_split_bars.png
* record/results/spreadsheet_*_s?of2.json -- SpreadsheetBench single-turn,
  baseline vs text_spreadsheet_edit. Figure: results_table_spreadsheet_split.png
* record/results_vllm/{full,drafts,chosen,explore} -- vLLM runs (src/evaluate_vllm.py,
  greedy, never mixed with the transformers cells). Figure: results_table_skill_search.png
  Re-score: python skill_search/analyze.py record/results_vllm/full record/results_vllm/chosen --subsets test,test:cw,meta
  (the table scripts read results/ and results_vllm/; copy record/ back there to re-render).

## Findings
* strength_audit gains only on META (+9 / +21 / +40 for 8B / 14B / 27B) and
  loses on OTHER (~-4 on held-out test). Without the meta step, 27B still gains
  +34 on META: the "distrust the strongest claim" stance finds the option alone.
* proof_sketch, held-out test OTHER (n=222): +2.7 / +5.9 / -0.9, mean +2.6;
  pooled McNemar p=0.25 vs baseline, p=0.65 vs a length-matched placebo (+1.5).
  Not significant. META unchanged. 27B truncates (48% hit 4096 tokens).
* proof_sketch_brief (500-word cap) was designed after dev results -- exploratory
  only: fixes 27B truncation, dev mean gain 0.0.
