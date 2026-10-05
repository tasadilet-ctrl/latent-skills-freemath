"""Does the model actually FOLLOW the skill, or merely have it in context?

Presence in the prompt is verifiable by tokenising (410 vs 36 tokens). Compliance
is not. If the with-skill generations look the same as the placebo ones, then the
"target behaviour" the embedding skill is being asked to reproduce barely differs
from baseline, and every fidelity number is measuring noise.

Prints all three conditions side by side for eyeballing, plus a crude marker
count for the procedure's observable surface (goal restatement, knowns list,
per-step arithmetic, explicit verification).
"""
from __future__ import annotations

import json
import os
import re
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import evaluate, qwen  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MARKERS = {
    "restates goal": r"(?i)\b(goal|we (?:need|want) to find|asked for|find(?:ing)?:)",
    "lists knowns": r"(?i)\b(known|given|we know|values?:)",
    "verification": r"(?i)\b(verif|check|sanity|substitut|confirm|plausib)",
    "backtrack": r"(?i)\b(backtrack|contradict|revisit|recompute)",
}


def markers(t):
    return {k: bool(re.search(v, t)) for k, v in MARKERS.items()}


def main():
    skill = open(os.path.join(ROOT, "skills", "decompose_verify.md")).read()
    placebo = open(os.path.join(ROOT, "skills", "placebo_matched.md")).read()

    rows = []
    with open(os.path.join(ROOT, "data", "gsm8k_train.jsonl")) as f:
        for line in f:
            rows.append(json.loads(line))
            if len(rows) >= 20:
                break

    tok, model, _ = qwen.load()
    conds = [("SKILL", skill), ("PLACEBO", placebo), ("NOTHING", None)]
    tally = {c: {k: 0 for k in MARKERS} for c, _ in conds}

    for i, r in enumerate(rows):
        q = r["question"] + evaluate.GSM_SUFFIX
        for name, sysmsg in conds:
            p = qwen.build_prompt(tok, q, system_msg=sysmsg)
            enc = tok(p, return_tensors="pt").to(qwen.first_param_device(model))
            with torch.no_grad():
                g = model.generate(**enc, max_new_tokens=320, do_sample=False,
                                   temperature=None, top_p=None, top_k=None,
                                   pad_token_id=tok.pad_token_id)
            out = tok.decode(g[0, enc["input_ids"].shape[1]:], skip_special_tokens=True)
            for k, v in markers(out).items():
                tally[name][k] += v
            if i < 2:
                print(f"\n{'='*70}\n### Q{i+1} [{name}]\n{'='*70}")
                print(out[:900])
        if (i + 1) % 5 == 0:
            print(f"\n[compliance] {i+1}/{len(rows)}", flush=True)

    n = len(rows)
    print(f"\n\n{'marker':<16} {'SKILL':>8} {'PLACEBO':>9} {'NOTHING':>9}   (of {n})")
    print("-" * 48)
    for k in MARKERS:
        print(f"{k:<16} {tally['SKILL'][k]:>8} {tally['PLACEBO'][k]:>9} {tally['NOTHING'][k]:>9}")


if __name__ == "__main__":
    main()
