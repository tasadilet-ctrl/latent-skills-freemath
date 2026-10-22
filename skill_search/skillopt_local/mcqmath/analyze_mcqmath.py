"""Final table for the mcqmath SkillOpt runs (PROTOCOL.md's final report, for MMLU-Pro and SuperGPQA math).

    python analyze_mcqmath.py [work dir] [model tag]

Every condition answered the identical test items (same server, same prompt, same
choice order), so tests are paired: exact McNemar against no-skill, and each skill
against its own length-matched placebo. Scores are split by centroid_right, the
PROTOCOL.md check for whether a gain lives only where the option-similarity
shortcut works.
"""
from __future__ import annotations

import json
import math
import os
import sys

W = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/skillopt_work")
TAG = sys.argv[2] if len(sys.argv) > 2 else "qwen3-8b"
CONDS = ["none", "placebo", "strength_audit", "placebo_ts", "livemath_ts", "skillopt"]
PAIRS = [("strength_audit", "placebo"), ("livemath_ts", "placebo_ts"), ("skillopt", "placebo")]


def mcnemar(a, b, ids):
    up = sum(1 for i in ids if not a[i] and b[i])
    down = sum(1 for i in ids if a[i] and not b[i])
    n = up + down
    p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, k) for k in range(min(up, down) + 1)) / 2 ** n)
    return up, down, p


def load(path):
    if not os.path.exists(path):
        return {}
    return {str(r["id"]): r for r in map(json.loads, open(path))}


for bench in ("mmlupro_math_tq_sb", "supergpqa_math_hard"):
    run = os.path.join(W, "outputs", f"mq_{bench}_{TAG}")
    if not os.path.isdir(run):
        continue
    test = {str(it["id"]): it for it in json.load(open(os.path.join(W, "mq_split", bench, "test", "items.json")))}
    res = {c: load(os.path.join(run, "final_eval", c, "results.jsonl")) for c in CONDS}
    if not res["none"]:
        continue
    hard = {c: {i: int(r.get("hard", 0)) for i, r in v.items()} for c, v in res.items() if v}
    ids = [i for i in test if all(i in h for h in hard.values())]
    groups = {"all": ids, "centroid-wrong": [i for i in ids if not test[i]["centroid_right"]],
              "centroid-right": [i for i in ids if test[i]["centroid_right"]]}
    print(f"\n== {bench} ({TAG})  test n={len(ids)}  centroid-right {len(groups['centroid-right'])}")
    for c in CONDS:
        if c not in hard:
            print(f"  {c:15s} (missing)")
            continue
        noans = sum(1 for i in ids if not str(res[c][i].get("predicted_label") or "").strip())
        cells = []
        for g, I in groups.items():
            if not I:
                continue
            acc = 100 * sum(hard[c][i] for i in I) / len(I)
            if c == "none":
                cells.append(f"{g} {acc:5.1f}")
            else:
                u, d, p = mcnemar(hard["none"], hard[c], I)
                cells.append(f"{g} {acc:5.1f}{'*' if p < 0.05 else ' '}(+{u}/-{d} p={p:.2g})")
        print(f"  {c:15s} no-label {noans:3d} | " + " | ".join(cells))
    for sk, pl in PAIRS:
        if sk in hard and pl in hard:
            u, d, p = mcnemar(hard[pl], hard[sk], ids)
            print(f"  {sk} vs {pl}: +{u}/-{d} p={p:.2g}")
    sp = os.path.join(run, "summary.json")
    if os.path.exists(sp):
        s = json.load(open(sp))
        print("  SkillOpt summary:", {k: s.get(k) for k in ("baseline_selection_hard", "best_selection_hard",
                                                             "total_accepts", "total_rejects", "total_wall_time_s")})
