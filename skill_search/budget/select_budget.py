"""Dev selection for skill_search/budget/PROTOCOL.md, or the test report.

    python select_budget.py ~/budget/results dev     # selection table + chosen draft
    python select_budget.py ~/budget/results test    # per-bench and pooled test cells, McNemar

Pooled score = accuracy over all items of the 7 benchmarks (items weighted equally), minus the
baseline's on the same items; the selection score is its mean over the 3 models.
"""
import glob
import json
import math
import os
import sys

D, SPLIT = os.path.expanduser(sys.argv[1]), sys.argv[2]
BENCHES = ["mmlupro_math_tq_sb", "supergpqa_math_hard", "beyondaime", "hardmath2", "realmath", "imoanswer", "arxivmath"]
SHORT = {"mmlupro_math_tq_sb": "MMLU-Pro", "supergpqa_math_hard": "SuperGPQA", "beyondaime": "BeyondAIME",
         "hardmath2": "HARDMath2", "realmath": "RealMath", "imoanswer": "IMO-Ans", "arxivmath": "ArxivMath"}
MODELS = ["qwen3-8b", "qwen3-14b", "qwen3.6-27b"]
DRAFTS = ["route_first", "route_first_short", "small_cases", "check_answer"]
CONTROLS = ["brevity_control", "placebo_notation"]


def load(b, m, s):
    f = f"{D}/{b}_{m}_{s}_{SPLIT}.json"
    if not os.path.exists(f):
        return None
    return {r["id"]: float(r["em"]) for r in json.load(open(f))["records"]}


def mcnemar(a, b):
    up = sum(1 for i in a if not a[i] and b[i]); dn = sum(1 for i in a if a[i] and not b[i]); n = up + dn
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, k) for k in range(min(up, dn) + 1)) / 2 ** n)


conds = ["baseline"] + DRAFTS + CONTROLS + (["livemath_ts"] if SPLIT == "test" else [])
cells = {}  # (m, s) -> {bench: {id: em}}
for m in MODELS:
    for s in conds:
        cells[m, s] = {b: load(b, m, s) for b in BENCHES}


def pooled(m, s):
    """Pooled em dicts over benches where both s and baseline exist; returns (s_em, base_em, missing)."""
    a, z, miss = {}, {}, []
    for b in BENCHES:
        x, y = cells[m, s][b], cells[m, "baseline"][b]
        if x is None or y is None:
            miss.append(SHORT[b]); continue
        a.update({(b, i): v for i, v in x.items()}); z.update({(b, i): y[i] for i in x})
    return a, z, miss


print(f"== {SPLIT}: accuracy gain vs baseline in points (per benchmark, then pooled over all items)")
hdr = f"{'model':12s} {'condition':18s}" + "".join(f"{SHORT[b]:>11s}" for b in BENCHES) + f"{'POOLED':>9s}{'p':>7s}"
score = {}
for m in MODELS:
    print(hdr)
    for s in conds:
        row = f"{m:12s} {s:18s}"
        for b in BENCHES:
            x, y = cells[m, s][b], cells[m, "baseline"][b]
            if x is None or y is None:
                row += f"{'-':>11s}"; continue
            acc = 100 * sum(x.values()) / len(x)
            row += f"{acc:6.1f}" + (f"{acc - 100 * sum(y.values()) / len(y):+5.1f}" if s != "baseline" else "     ")
        a, z, miss = pooled(m, s)
        if a:
            g = 100 * (sum(a.values()) - sum(z.values())) / len(a)
            score.setdefault(s, {})[m] = (g, miss)
            row += f"{(100 * sum(a.values()) / len(a)) if s == 'baseline' else g:+9.2f}" if s != "baseline" else f"{100 * sum(a.values()) / len(a):9.1f}"
            row += f"{mcnemar(z, a):7.3f}" if s != "baseline" else ""
        print(row + (f"  (missing: {', '.join(miss)})" if miss else ""))
    print()

if SPLIT == "dev":
    print("== selection score = pooled gain, mean over models (needs all 3 models and all 7 benchmarks)")
    words = {s: len(open(p).read().split()) for s in DRAFTS + CONTROLS
             for p in glob.glob(os.path.expanduser(f"~/budget/skills/{s}.md")) + glob.glob(os.path.expanduser(f"~/mcq_math/skills/{s}.md"))}
    tab = {}
    for s in DRAFTS + CONTROLS:
        v = score.get(s, {})
        complete = len(v) == 3 and not any(miss for _, miss in v.values())
        mean = sum(g for g, _ in v.values()) / max(1, len(v))
        tab[s] = (mean, complete, sum(g > 0 for g, _ in v.values()))
        print(f"  {s:18s} {mean:+6.2f}  models>0: {tab[s][2]}/3  {'complete' if complete else 'INCOMPLETE'}  {words.get(s, '?')} words")
    ctrl = max(tab[c][0] for c in CONTROLS)
    ok = [s for s in DRAFTS if tab[s][1] and tab[s][0] > ctrl and tab[s][0] > 0 and tab[s][2] >= 2]
    if not all(tab[s][1] for s in DRAFTS + CONTROLS):
        print("-> not all cells done; no choice yet")
    elif not ok:
        print("-> no draft qualifies (above both controls, above baseline on >= 2 of 3 models): none found")
    else:
        best = max(tab[s][0] for s in ok)
        tied = [s for s in ok if best - tab[s][0] <= 0.5]
        chosen = min(tied, key=lambda s: words.get(s, 1e9))
        print(f"-> chosen: {chosen} (score {tab[chosen][0]:+.2f}; best control {ctrl:+.2f})")
else:
    print("== test: chosen vs each control, pooled, exact McNemar")
    for m in MODELS:
        for s in DRAFTS:
            if not any(cells[m, s].values()):
                continue
            for c in CONTROLS + ["livemath_ts"]:
                A, _, _ = pooled(m, s); C, _, _ = pooled(m, c)
                k = set(A) & set(C)
                if k:
                    a = {i: A[i] for i in k}; cc = {i: C[i] for i in k}
                    print(f"  {m:12s} {s} vs {c:18s} {100 * (sum(a.values()) - sum(cc.values())) / len(k):+6.2f}  p={mcnemar(cc, a):.3f}  n={len(k)}")
