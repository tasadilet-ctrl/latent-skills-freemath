import json, math, os, re
os.chdir(os.path.expanduser("~/rg_gepa"))
USED = set(range(1, 71))           # screen 1..60, GEPA train 11..70, val 12..51, vector train 21..60, dev 22..37
CLEAN = [i for i in range(200) if i not in USED]
def mcn(a, b, ids):
    up = sum(1 for i in ids if not a[i] and b[i]); dn = sum(1 for i in ids if a[i] and not b[i]); n = up + dn
    return up, dn, (1.0 if n == 0 else min(1.0, 2*sum(math.comb(n, j) for j in range(min(up, dn)+1))/2**n))
acc = lambda d, ids: 100*sum(d[i] for i in ids)/len(ids)
print(f"clean test items: {len(CLEAN)} (indices 0 and 71-199)\n")
print("GEPA test (vLLM), default split: all 200 vs clean")
for m, t in (("qwen3-8b","products"),("qwen3-14b","products"),("qwen3-14b","decimal_arithmetic"),("qwen3-8b","word_sorting")):
    C = {}
    for c in ("none","placebo","seed","gepa"):
        C[c] = {r["idx"]: r["correct"] for r in map(json.loads, open(f"test/{m}/default_{c}.jsonl")) if r["task"] == t}
    used = [i for i in range(200) if i in USED]
    s = "  ".join(f"{c}={acc(C[c], range(200)):.1f}/{acc(C[c], CLEAN):.1f}/{acc(C[c], used):.1f}" for c in C)
    tests = " ".join(f"vs {c}: +{u}/-{d} p={p:.1g}" for c in ("none","placebo","seed") for u, d, p in [mcn(C[c], C["gepa"], CLEAN)])
    print(f"  {m} {t:20s} (all/clean/used) {s}\n      clean: {tests}")
print("\nVector arm (HF), clean items only")
for b, t in (("decimal_arithmetic","qwen3-14b"),("products","qwen3-8b"),("products","qwen3-14b"),("word_sorting","qwen3-8b")):
    import reasoning_gym as rg
    ds = rg.create_dataset(b, size=200, seed=0); ok = {}
    for c in ("baseline","placebo","text","B1","B2","CONTROL"):
        d = json.load(open(f"vec/out/results/{b}_{t}_{c}_test.json"))["records"]; ok[c] = {}
        for r in d:
            i = int(r["id"].rsplit("-",1)[1]); mm = re.findall(r"<answer>(.*?)</answer>", r["raw"], re.S)
            try: ok[c][i] = bool(mm) and ds.score_answer(mm[-1].strip(), ds[i]) >= 1.0
            except Exception: ok[c][i] = False
    print(f"  {b} {t}: " + "  ".join(f"{c}={acc(ok[c], CLEAN):.1f}" for c in ok))
    for x, y in (("text","placebo"),("B1","CONTROL"),("B2","CONTROL"),("B1","text"),("B2","text")):
        u, d, p = mcn(ok[y], ok[x], CLEAN); print(f"      {x} vs {y}: +{u}/-{d} p={p:.2g}")
