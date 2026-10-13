"""Score every vLLM cell by subset.

    python skill_search/analyze.py results_vllm/drafts results_vllm/full [--subsets dev]

Subsets: dev / test (OTHER questions, split.json), meta, and the
centroid-wrong part of each OTHER subset (questions where the text-similarity
shortcut points at a wrong option -- a gain there cannot come from the shortcut).
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import math
import os

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPLIT = json.load(open(os.path.join(KIT, "skill_search", "split.json")))
MODELS = ["qwen3-8b", "qwen3-14b", "qwen3.6-27b"]


def mcnemar(a, b):
    sh = set(a) & set(b)
    b01 = sum(1 for i in sh if not a[i] and b[i])
    b10 = sum(1 for i in sh if a[i] and not b[i])
    n = b01 + b10
    if not n:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(min(b01, b10) + 1)) / 2 ** n)


def load(dirs):
    cells = collections.defaultdict(dict)   # (model, cond) -> id -> rec
    for d in dirs:
        for p in glob.glob(os.path.join(KIT, d, "*.json")):
            b = json.load(open(p))
            s = b["summary"]
            for r in b["records"]:
                cells[(s["model_tag"], s["condition"])][r["id"]] = r
    return cells


def subset(name):
    if name == "meta":
        return {k for k, v in SPLIT.items() if v["split"] == "meta"}
    base, _, cw = name.partition(":")
    ids = {k for k, v in SPLIT.items() if v["split"] in (base.split("+"))}
    if cw == "cw":
        ids = {k for k in ids if not SPLIT[k]["centroid_right"]}
    if cw == "cr":
        ids = {k for k in ids if SPLIT[k]["centroid_right"]}
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--subsets", default="dev,dev:cr,dev:cw")
    args = ap.parse_args()
    cells = load(args.dirs)
    subs = args.subsets.split(",")
    conds = sorted({c for _, c in cells}, key=lambda c: (c != "baseline", c))
    mean_gain = collections.defaultdict(list)
    for m in MODELS:
        base = cells.get((m, "baseline"))
        if not base:
            continue
        print(f"\n### {m}")
        print(f"{'condition':28}" + "".join(f"{s:>22}" for s in subs) + "   toks  capped")
        for c in conds:
            it = cells.get((m, c))
            if not it:
                continue
            line = f"{c:28}"
            for s in subs:
                ids = subset(s) & set(it) & set(base)
                if not ids:
                    line += f"{'-':>22}"; continue
                acc = 100 * sum(it[i]["em"] for i in ids) / len(ids)
                bacc = 100 * sum(base[i]["em"] for i in ids) / len(ids)
                p = mcnemar({i: base[i]["em"] > 0 for i in ids}, {i: it[i]["em"] > 0 for i in ids})
                star = "*" if p < 0.05 and c != "baseline" else " "
                line += f"{acc:6.1f} ({acc-bacc:+5.1f}){star} n={len(ids):<4}"
                if c != "baseline":
                    mean_gain[(c, s)].append(acc - bacc)
            toks = sum(r.get("gen_tokens", 0) for r in it.values()) / len(it)
            cap = 4096 if "27b" in m else 2048
            forced = sum(1 for r in it.values() if r.get("gen_tokens", 0) >= cap) / len(it)
            print(line + f"  {toks:5.0f}  {100*forced:4.1f}%")
    print("\n### mean gain over models (pts vs baseline)")
    for c in conds[1:]:
        vals = [f"{s}: {sum(mean_gain[(c, s)])/len(mean_gain[(c, s)]):+5.1f} (k={len(mean_gain[(c, s)])})"
                for s in subs if mean_gain[(c, s)]]
        print(f"{c:28} " + "   ".join(vals))


if __name__ == "__main__":
    main()
