"""Apply the PROTOCOL.md rule to test results. usage: analyze.py <model_tag>"""
import json, re, sys, collections
from math import comb
import reasoning_gym as rg
tag = sys.argv[1]; T = f"test/{tag}"

def load(p):
    d = collections.defaultdict(dict)
    for l in open(p):
        r = json.loads(l); d[r["task"]][r["idx"]] = r
    return d

def mcnemar(a, b):  # exact two-sided; a, b dicts idx->row
    w = sum(a[i]["correct"] and not b[i]["correct"] for i in a); l = sum(b[i]["correct"] and not a[i]["correct"] for i in a)
    n = w + l
    if n == 0: return w, l, 1.0
    k = min(w, l); p = min(1.0, 2 * sum(comb(n, j) for j in range(k + 1)) / 2 ** n)
    return w, l, p

def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i]); out = [False] * len(ps)
    for r, i in enumerate(order):
        if ps[i] * (len(ps) - r) < 0.05: out[i] = True
        else: break
    return out

def leaks(task, skill):
    hits = []
    for seed, n in ((11, 60), (12, 40)):
        d = rg.create_dataset(task, size=n, seed=seed)
        for i in range(n):
            e = d[i]; ans = str(e["answer"]).strip()
            if len(ans) >= 4 and ans in skill: hits.append(f"answer:{ans[:30]}")
            for num in set(re.findall(r"\d{3,}", e["question"])):
                if re.search(rf"(?<!\d){num}(?!\d)", skill): hits.append(f"number:{num}")
    return sorted(set(hits))

acc = lambda rs: 100 * sum(r["correct"] for r in rs.values()) / len(rs)
for split in ("default", "hard"):
    C = {c: load(f"{T}/{split}_{c}.jsonl") for c in ("none", "seed", "placebo", "brevity", "gepa")}
    print(f"\n== {tag} {split} (test seed 0, n=200)")
    print(f"{'task':26s} {'none':>5s} {'seed':>5s} {'plac':>5s} {'brev':>5s} {'GEPA':>5s}  vs none / plac / seed (p)" + ("   found  words  leaks" if split == "default" else ""))
    for t in sorted(C["gepa"]):
        a = {c: acc(C[c][t]) for c in C}
        tests = [mcnemar(C["gepa"][t], C[c][t]) for c in ("none", "placebo", "seed")]
        sig = holm([p for _, _, p in tests])
        gain_ok = a["gepa"] - a["placebo"] >= 10
        line = f"{t:26s} " + " ".join(f"{a[c]:5.1f}" for c in ("none", "seed", "placebo", "brevity", "gepa")) + "  " + \
               " / ".join(f"{a['gepa']-a[c]:+.1f}({p:.1g}{'*' if s else ''})" for c, (_, _, p), s in zip(("none", "placebo", "seed"), tests, sig))
        if split == "default":
            skill = open(f"gepa/{tag}/{t}/skill.md").read(); lk = leaks(t, skill)
            found = all(sig) and all(a["gepa"] > a[c] for c in ("none", "placebo", "seed")) and gain_ok and not lk
            line += f"   {'FOUND' if found else '-':5s}  {len(skill.split()):4d}  {';'.join(lk[:3]) or 'none'}"
        print(line)
