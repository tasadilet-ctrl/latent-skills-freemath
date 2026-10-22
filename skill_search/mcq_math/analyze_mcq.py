"""Table for evaluate_vllm_mcq.py results: paired exact McNemar vs baseline, split by centroid.

    python analyze_mcq.py <results dir> [model tag]
"""
from __future__ import annotations

import glob
import json
import math
import os
import sys

D = sys.argv[1]
TAG = sys.argv[2] if len(sys.argv) > 2 else "qwen3-8b"
ORDER = ["baseline", "placebo_matched", "strength_audit", "placebo_livemath_ts", "livemath_ts"]


def mcnemar(a, b, ids):
    up = sum(1 for i in ids if not a[i] and b[i])
    down = sum(1 for i in ids if a[i] and not b[i])
    n = up + down
    p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, k) for k in range(min(up, down) + 1)) / 2 ** n)
    return up, down, p


for bench in sorted({os.path.basename(f).split(f"_{TAG}_")[0] for f in glob.glob(os.path.join(D, f"*_{TAG}_*.json"))}):
    res = {}
    for f in glob.glob(os.path.join(D, f"{bench}_{TAG}_*.json")):
        b = json.load(open(f))
        res[b["summary"]["skill"]] = ({r["id"]: r for r in b["records"]}, b["summary"])
    if "baseline" not in res:
        continue
    base = {i: r["em"] for i, r in res["baseline"][0].items()}
    ids = list(base)
    split = {"all": ids,
             "centroid-wrong": [i for i in ids if not res["baseline"][0][i]["centroid_right"]],
             "centroid-right": [i for i in ids if res["baseline"][0][i]["centroid_right"]]}
    print(f"\n== {bench}  ({TAG})  n={len(ids)}  (centroid-right {len(split['centroid-right'])})")
    for name in [n for n in ORDER if n in res] + sorted(set(res) - set(ORDER)):
        recs, s = res[name]
        h = {i: r["em"] for i, r in recs.items()}
        cells = []
        for k, I in split.items():
            if not I:
                continue
            acc = 100 * sum(h[i] for i in I) / len(I)
            if name == "baseline":
                cells.append(f"{k} {acc:5.1f}")
            else:
                up, down, p = mcnemar(base, h, I)
                cells.append(f"{k} {acc:5.1f}{'*' if p < 0.05 else ' '} (+{up}/-{down} p={p:.2g})")
        print(f"  {name:20s} parse {s['parse_rate']:.3f} forced {s['forced']:3d} | " + " | ".join(cells))
