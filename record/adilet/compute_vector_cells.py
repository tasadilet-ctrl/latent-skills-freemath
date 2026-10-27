"""Cells for make_vector_table.py, from the vector arm's saved per-question results (run on the box).

    python compute_vector_cells.py [~/vec_arm] > vector_cells.json

Every cell is paired with its row's HF-engine baseline on identical items: exact two-sided McNemar.
Fidelity (1 - KL(text||steered)/KL(text||plain), 16 dev items) is at the fixed operating point.
"""
import json
import math
import os
import sys

D = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/vec_arm")
BENCHES = [("mmlupro_math_tq_sb", "MMLU-Pro math"), ("supergpqa_math_hard", "SuperGPQA hard math")]
MODELS = [("qwen3-8b", "Qwen 3 8b", 34), ("qwen3-14b", "Qwen 3 14b", 37), ("qwen3.6-27b", "Qwen 3.6 27b", 62)]
CONDS = ["baseline", "text", "placebo", "B1", "B2", "CONTROL"]


def mcnemar(a, b):
    up = sum(1 for i in a if not a[i] and b[i])
    dn = sum(1 for i in a if a[i] and not b[i])
    n = up + dn
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, k) for k in range(min(up, dn) + 1)) / 2 ** n)


rows = []
for b, blab in BENCHES:
    for m, mlab, L in MODELS:
        em = {}
        for c in CONDS:
            f = f"{D}/results/{b}_{m}_{c}_test.json"
            if os.path.exists(f):
                em[c] = {r["id"]: float(r["em"]) for r in json.load(open(f))["records"]}
        if "baseline" not in em:
            continue
        base = em["baseline"]
        b_acc = 100 * sum(base.values()) / len(base)
        cells = {}
        for c, rec in em.items():
            assert set(rec) == set(base), (b, m, c)
            a = 100 * sum(rec.values()) / len(rec)
            cells[c] = {"acc": a, "n": len(rec), "d": a - b_acc, "p": None if c == "baseline" else mcnemar(base, rec)}
        fid = {}
        ff = f"{D}/fidelity_{m}_{b}.json"
        if os.path.exists(ff):
            fid = {arm: v.get(f"L{L}_g0.3") for arm, v in json.load(open(ff)).items()}
        rows.append({"bench": blab, "model": mlab, "layer": L, "cells": cells, "fidelity": fid})
print(json.dumps(rows, indent=1))
