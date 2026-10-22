"""Final table for the freemath SkillOpt runs (PROTOCOL.md's report, for free-form benchmarks).

    python analyze_freemath.py [work dir] [model tag]     default: ~/skillopt_work qwen3-8b

For each benchmark, every condition answered the identical test items (same
vLLM server, same prompt), so the test is paired: exact two-sided McNemar on the
discordant items, against the no-skill row. Also prints SkillOpt's own
baseline/test numbers from summary.json as a cross-check, and how many of the
skillopt condition's correct answers came from the numeric (vs symbolic) check.
"""
from __future__ import annotations

import json
import math
import os
import sys
from collections import Counter

W = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/skillopt_work")
TAG = sys.argv[2] if len(sys.argv) > 2 else "qwen3-8b"
EVAL_DIR = sys.argv[3] if len(sys.argv) > 3 else "final_eval"     # or final_eval_forced
CONDS = ["none", "placebo", "strength_audit", "skillopt"]


def mcnemar(a: dict, b: dict) -> tuple[int, int, float]:
    ids = set(a) & set(b)
    up = sum(1 for i in ids if not a[i] and b[i])
    down = sum(1 for i in ids if a[i] and not b[i])
    n = up + down
    if n == 0:
        return up, down, 1.0
    tail = sum(math.comb(n, k) for k in range(min(up, down) + 1)) / 2 ** n
    return up, down, min(1.0, 2 * tail)


def load(path: str) -> dict:
    out = {}
    if os.path.exists(path):
        for line in open(path):
            r = json.loads(line)
            out[str(r["id"])] = r
    return out


for bench in ("beyondaime", "hardmath2", "realmath", "arxivmath", "imoanswer"):
    run = os.path.join(W, "outputs", f"fm_{bench}_{TAG}")
    if not os.path.isdir(run):
        continue
    def _res(c):
        d = os.path.join(run, EVAL_DIR, c)
        orig = load(os.path.join(d, "results.jsonl"))
        resc = load(os.path.join(d, "results_rescored.jsonl"))   # rescore_freemath.py
        # a rescore cut off mid-file (a reboot did this once) must not replace the full run
        return resc if resc and len(resc) == len(orig) else orig
    res = {c: _res(c) for c in CONDS}
    base = {i: r["hard"] for i, r in res["none"].items()}
    print(f"\n== {bench}  ({TAG}, {EVAL_DIR})  test n={len(base)}")
    for c in CONDS:
        if not res[c]:
            print(f"  {c:15s} (missing)")
            continue
        h = {i: r["hard"] for i, r in res[c].items()}
        acc = 100 * sum(h.values()) / len(h)
        if c == "none":
            print(f"  {c:15s} {acc:5.1f}   n={len(h)}")
            continue
        up, down, p = mcnemar(base, h)
        star = "*" if p < 0.05 else " "
        print(f"  {c:15s} {acc:5.1f}{star}  n={len(h)}  +{up}/-{down}  McNemar p={p:.3g}")
    if res["skillopt"]:
        how = Counter(r.get("match_method", "") for r in res["skillopt"].values() if r["hard"])
        nobox = sum(1 for r in res["skillopt"].values() if r.get("match_method") == "no_final_answer")
        print(f"  skillopt correct by check: {dict(how)};  replies without a final answer: {nobox}")
        print("  truncated (no final answer / forced) per condition:",
              {c: f"{sum(1 for r in res[c].values() if r.get('match_method') == 'no_final_answer')}"
                  f"/{sum(1 for r in res[c].values() if r.get('forced'))}" for c in CONDS if res[c]})
        types = sorted({r.get("task_type", "") for r in res["none"].values()})
        if len(types) > 1:
            for t in types:
                ids = [i for i, r in res["none"].items() if r.get("task_type") == t]
                b = 100 * sum(base[i] for i in ids) / len(ids)
                s = 100 * sum(res["skillopt"][i]["hard"] for i in ids if i in res["skillopt"]) / len(ids)
                print(f"    {t:22s} n={len(ids):3d}  none {b:5.1f}  skillopt {s:5.1f}")
    sp = os.path.join(run, "summary.json")
    if os.path.exists(sp):
        s = json.load(open(sp))
        keys = ("baseline_test_hard", "test_hard", "baseline_selection_hard", "best_selection_hard",
                "total_accepts", "total_rejects", "total_wall_time_s")
        print("  SkillOpt summary:", {k: s.get(k) for k in keys})
