"""Test report for GEPA math-suite skills (PROTOCOL.md rules) + leak check.  python analyze.py [models...]"""
import json, os, re, sys, glob
from math import comb
H = os.path.expanduser("~"); D = f"{H}/math_gepa"
MCQ = ("mmlupro_math_tq_sb", "supergpqa_math_hard")
BENCH = ["mmlupro_math_tq_sb", "supergpqa_math_hard", "beyondaime", "hardmath2", "realmath", "imoanswer", "arxivmath"]
TAGS = sys.argv[1:] or ["qwen3-8b", "qwen3-14b"]

def cell(bench, tag, name, new):
    base = (f"{D}/results" if new else f"{H}/budget/results") + ("" if bench in MCQ else "_mv")
    f = f"{base}/{bench}_{tag}_{name}_test.json"
    if not os.path.exists(f): return None
    return {r["id"]: r["em"] for r in json.load(open(f))["records"]}

def mcnemar(a, b):
    w = sum(a[i] > b[i] for i in a); l = sum(a[i] < b[i] for i in a); n = w + l
    p = min(1.0, 2 * sum(comb(n, k) for k in range(min(w, l) + 1)) / 2 ** n) if n else 1.0
    return w, l, p

def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i]); adj = [0] * len(ps); run = 0
    for r, i in enumerate(order):
        run = max(run, (len(ps) - r) * ps[i]); adj[i] = min(1.0, run)
    return adj

def words(s): return re.findall(r"[a-z0-9]+", s.lower())

sys.path.insert(0, D)
import gepa_math as g
for tag in TAGS:
    print(f"\n===== {tag}  (test split; free-form scored with math_verify)")
    pooled = {k: [] for k in ["baseline", "placebo_notation", "brevity_control", "seed_skill", "gepa"]}
    for b in BENCH:
        c = {k: cell(b, tag, k, False) for k in ["baseline", "placebo_notation", "brevity_control"]}
        c["seed_skill"] = cell(b, tag, "seed_skill", True); c["gepa"] = cell(b, tag, f"gepa_{b}", True)
        if any(v is None for v in c.values()):
            print(f"{b:22s} missing: {[k for k, v in c.items() if v is None]}"); continue
        acc = {k: 100 * sum(v.values()) / len(v) for k, v in c.items()}
        for k in pooled: pooled[k].append(acc[k])
        tests = [mcnemar(c["gepa"], c[k]) for k in ["baseline", "placebo_notation", "brevity_control", "seed_skill"]]
        adj = holm([t[2] for t in tests])
        win = all(t[0] > t[1] for t in tests) and all(p < 0.05 for p in adj) and acc["gepa"] - acc["placebo_notation"] >= 5
        # leak check: 8-word spans of train/val questions, and gold answers (>=4 chars) found in the skill text
        skill = open(f"{D}/gepa/{tag}/{b}/skill.md").read(); sw = " ".join(words(skill)); hits = []
        tr, va = g.load(b)
        for r in tr + va:
            q = words(r["question"])
            if any(" ".join(q[i:i + 8]) in sw for i in range(max(0, len(q) - 7))): hits.append(f"q:{r['id']}")
            gold = r["options"][ord(r["answer"]) - 65] if b in MCQ else r["answer"]
            if len(str(gold)) >= 4 and str(gold) in skill: hits.append(f"a:{r['id']}")
        n = len(c["gepa"])
        print(f"{b:22s} n={n:3d} none={acc['baseline']:5.1f} placebo={acc['placebo_notation']:5.1f} brevity={acc['brevity_control']:5.1f} "
              f"seed={acc['seed_skill']:5.1f} GEPA={acc['gepa']:5.1f} | " +
              " ".join(f"vs {k[:7]} +{t[0]}/-{t[1]} p={a:.2g}" for k, t, a in zip(["none", "placebo", "brevity", "seed"], tests, adj)) +
              f" | {'FOUND' if win and not hits else 'no'}{' LEAK ' + ','.join(hits[:5]) if hits else ''}")
    if pooled["gepa"]:
        print(f"{'POOLED (mean of benches)':22s}       " + " ".join(f"{k}={sum(v)/len(v):5.1f}" for k, v in pooled.items()))
    for b in BENCH:
        h = f"{D}/gepa/{tag}/{b}/history.json"
        if os.path.exists(h):
            j = json.load(open(h)); print(f"  val {b:22s} seed={100*j['val_scores'][0]:5.1f} best={100*j['val_scores'][j['best_idx']]:5.1f} cands={len(j['candidates'])}")
