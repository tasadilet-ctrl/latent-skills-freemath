"""LiveMath table with the livemath_ts skill added next to the skill-search cells.
Same rows as src/make_skill_search_table_png.py, plus an all-OTHER row: livemath_ts
was written without seeing the dev/test split, so all 345 OTHER questions are fair
for it (proof_sketch's all-OTHER cell includes the dev questions it was selected on)."""
from __future__ import annotations

import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.make_meta_split_table_png import render  # noqa: E402

MODELS = ["qwen3-8b", "qwen3-14b", "qwen3.6-27b"]
COLS = ["baseline", "placebo_matched", "strength_audit", "strength_audit_nometa",
        "proof_sketch", "livemath_ts"]
PRETTY = {"baseline": "baseline\n(no skill)",
          "placebo_matched": "placebo\n(length-matched)",
          "strength_audit": "strength_audit\n(Adilet's skill)",
          "strength_audit_nometa": "strength_audit\nminus meta rule",
          "proof_sketch": "proof_sketch\n(chosen on dev)",
          "livemath_ts": "livemath_ts\n(new skill)"}
SPLIT = json.load(open(os.path.join(ROOT, "skill_search", "split.json")))
SUBSETS = [("all OTHER", "all 345 maths-only questions", lambda v: v["split"] != "meta"),
           ("test OTHER", "held-out 222", lambda v: v["split"] == "test"),
           ("test centroid-wrong", "similarity shortcut fails",
            lambda v: v["split"] == "test" and not v["centroid_right"]),
           ("META", "meta-option present", lambda v: v["split"] == "meta")]
SCALE = 20


def load(model, cond):
    out = {}
    for d in ("full", "drafts", "chosen", "ts"):
        for p in glob.glob(os.path.join(ROOT, "results_vllm", d, f"livemath_{model}_{cond}_s*.json")):
            for r in json.load(open(p))["records"]:
                out[r["id"]] = r["em"] > 0
    return out


def main():
    rows = []
    for m in MODELS:
        full = {c: load(m, c) for c in COLS}
        for name, desc, keep in SUBSETS:
            ids = {i for i, v in SPLIT.items() if keep(v)}
            cells = {c: {i: v for i, v in full[c].items() if i in ids} for c in COLS}
            rows.append((m, name, desc, cells))
    render(rows, COLS, PRETTY, "LiveMath: livemath_ts vs earlier skills (vLLM, greedy)",
           ["livemath_ts pooled over models, all 345 OTHER: +4.0 pts vs baseline (p=0.02), "
            "+2.8 vs placebo (p=0.10). proof_sketch's all-OTHER cell includes the dev set it was chosen on.",
            "centroid-wrong = questions where picking the option most similar to the others "
            "(a 68%-accurate no-model shortcut) is wrong."],
           SCALE, os.path.join(ROOT, "results_table_livemath_ts.png"))


if __name__ == "__main__":
    main()
