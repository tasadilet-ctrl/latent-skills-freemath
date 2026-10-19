"""LiveMath tables for Microsoft SkillOpt's released skill (GPT-5.5-optimized).

Two PNGs, each engine against its own baseline:
  results_table_skillopt_text.png  vLLM: TS full / nometa and their token-matched placebos (8B, 14B, 27B)
  results_table_skillopt_embed.png HF transformers: TS full and three steering arms (8B, 27B)
Subsets and loaders come from skill_search/skillopt/analyze.py.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "skill_search", "skillopt"))
from src.make_meta_split_table_png import render  # noqa: E402
import analyze as A  # noqa: E402

SUBSETS = [("main", "556 = 608 minus SkillOpt train+val", "main"),
           ("main OTHER", "no meta option", "main:OTHER"),
           ("main META", "meta option present (always correct)", "main:META"),
           ("SkillOpt test", "their 125 test items", "so_test"),
           ("SkillOpt train+val", "52, skill tuned on these", "trainval")]
SCALE = 25
NOTE_SUB = ("main excludes the 52 questions SkillOpt's optimizer saw; the train+val row is a "
            "contamination check only.")


def rows_for(cells, models, cols):
    rows = []
    for m in models:
        if any(len(cells.get((m, c), {})) != 608 for c in cols):
            print(f"skip {m}: incomplete {[(c, len(cells.get((m, c), {}))) for c in cols]}")
            continue
        for name, desc, key in SUBSETS:
            ids = A.SUBSETS[key]
            rows.append((m, name, desc, {c: {i: bool(cells[(m, c)][i]["em"]) for i in ids} for c in cols}))
    return rows


def main():
    cols = ["baseline", "TS full", "TS nometa"]
    pretty = {"baseline": "baseline\n(no skill)",
              "placebo, len-matched full": "placebo\n(643-token match)",
              "TS full": "SkillOpt skill\n(as released)",
              "placebo, len-matched nometa": "placebo\n(565-token match)",
              "TS nometa": "SkillOpt skill\nminus meta rule"}
    rows = rows_for(A.load_vllm(), A.MODELS, cols)
    if rows:
        render(rows, cols, pretty, "LiveMath: Microsoft SkillOpt skill as text (vLLM, greedy)",
               [NOTE_SUB, "minus meta rule = the two bullets about the 'stronger result can be proven' "
                "option removed; everything else unchanged."],
               SCALE, os.path.join(ROOT, "results_table_skillopt_text.png"))

    cols = ["baseline", "TS full", "ES vs-dummy", "ES vs-nothing", "placebo vector"]
    pretty = {"baseline": "baseline\n(no skill)", "TS full": "SkillOpt skill\nas text",
              "ES vs-dummy": "vector:\nskill - placebo", "ES vs-nothing": "vector:\nskill - nothing",
              "placebo vector": "vector:\nplacebo - nothing"}
    rows = rows_for(A.load_hf(), ["qwen3-8b", "qwen3.6-27b"], cols)
    if rows:
        render(rows, cols, pretty, "LiveMath: SkillOpt skill as text vs as steering vector (HF transformers)",
               [NOTE_SUB, "vectors: 50 SkillOpt train+val prompts; 8B layer 34, 27B layer 62, gamma 0.3 "
                "(relative); 2048 / 4096 new tokens."],
               SCALE, os.path.join(ROOT, "results_table_skillopt_embed.png"))


if __name__ == "__main__":
    main()
