"""Render the held-out result of the LiveMath skill search (skill_search/PROTOCOL.md)
as a PNG table: test-OTHER, its centroid-wrong part, and META, per model.
All cells come from the vLLM runner (results_vllm/), never mixed with results/.
"""
from __future__ import annotations

import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.make_meta_split_table_png import render  # noqa: E402

MODELS = ["qwen3-8b", "qwen3-14b", "qwen3.6-27b"]
COLS = ["baseline", "placebo_matched", "strength_audit", "strength_audit_nometa", "proof_sketch"]
PRETTY = {"baseline": "baseline\n(no skill)",
          "placebo_matched": "placebo\n(length-matched)",
          "strength_audit": "strength_audit\n(Adilet's skill)",
          "strength_audit_nometa": "strength_audit\nminus meta rule",
          "proof_sketch": "proof_sketch\n(chosen on dev)"}
SPLIT = json.load(open(os.path.join(ROOT, "skill_search", "split.json")))
SUBSETS = [("test OTHER", "held-out, all options maths",
            lambda v: v["split"] == "test"),
           ("test centroid-wrong", "similarity shortcut fails",
            lambda v: v["split"] == "test" and not v["centroid_right"]),
           ("META", "meta-option present", lambda v: v["split"] == "meta")]
SCALE = 20


def load(model, cond):
    out = {}
    for d in ("full", "chosen"):
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
            rows.append((m, name, desc, {c: {i: v for i, v in full[c].items() if i in ids}
                                         for c in COLS}))
    render(rows, COLS, PRETTY, "LiveMath skill search: held-out test (vLLM, greedy)",
           ["proof_sketch was picked from 3 drafts on 123 dev questions by a rule fixed in "
            "advance; test was run once.",
            "centroid-wrong = questions where picking the option most similar to the others "
            "(a 68%-accurate no-model shortcut) is wrong."],
           SCALE, os.path.join(ROOT, "results_table_skill_search.png"))


if __name__ == "__main__":
    main()
