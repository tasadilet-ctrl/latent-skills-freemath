# Does GEPA cheat? (2026-11-02, all 138 candidates of the 13 finished math-suite runs; 14B HARDMath2 pending)

Scripts: scratchpad audit.py / kw.py (copied logic: 8-word spans of every train, val and test question; every gold
answer >= 6 chars (MCQ: the correct option's text); keyword scan; per-item val scores from gepa_state.bin).

1. Copied problems or answers: none. No candidate shares an 8-word span with any train, val or test question, and
   no candidate contains a gold answer.
2. Option-guessing rules: none. 31 candidates use a flagged word; every such sentence is either an instruction
   AGAINST using the options' form ("avoid relying on superficial similarities between answer choices") or ordinary
   maths ("eliminate variables", "self-similar solutions"). Caveat: our reflection prompt forbids guessing rules;
   SkillOpt's optimizer prompt did not.
3. Benchmark priors / constants: none. One sentence in all 138 candidates contains a formula
   (BeyondAIME 14B cand 11: "f(x) + f(1 - x) = 1", a textbook symmetry); it occurs in no BeyondAIME question and was
   not selected. HARDMath2 candidates name methods (WKB, matched asymptotics, self-similar solutions), not answers.
4. Behaviour on MCQ val (selected skill vs seed skill, split by whether the option-similarity shortcut is right):
   | model | bench | centroid-right | centroid-wrong |
   |---|---|---|---|
   | 8B | MMLU-Pro | 70.0 -> 80.0 (+2/-1, n=10) | 75.6 -> 75.6 (+4/-4, n=90) |
   | 8B | SuperGPQA | 53.3 -> 60.0 (+2/-1, n=15) | 20.0 -> 31.8 (+14/-4, n=85) |
   | 14B | MMLU-Pro | 90.0 -> 90.0 (n=10) | 76.7 -> 80.0 (+3/-0, n=90) |
   | 14B | SuperGPQA | 40.0 -> 46.7 (+4/-3, n=15) | 36.5 -> 47.1 (+14/-5, n=85) |
   The SuperGPQA gains are on items the shortcut gets WRONG, so they are not the shortcut. Dev only; repeat on test.
