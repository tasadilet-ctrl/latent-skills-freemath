import json, os, glob, torch, hashlib
os.chdir(os.path.expanduser("~/rg_gepa/vec"))
P = [("products","qwen3-8b"),("products","qwen3-14b"),("decimal_arithmetic","qwen3-14b"),("polynomial_multiplication","qwen3-8b"),("word_sorting","qwen3-8b")]
L = {"qwen3-8b": 34, "qwen3-14b": 37}
print("1) train/dev vs test question overlap")
for b in ("products","decimal_arithmetic","polynomial_multiplication","word_sorting"):
    te = {r["question"] for r in json.load(open(f"items/{b}_test.json"))}
    for s in ("train","dev"):
        tr = [r["question"] for r in json.load(open(f"items/{b}_{s}.json"))]
        print(f"   {b:26s} {s}: {sum(q in te for q in tr)}/{len(tr)} in test")
print("2) vectors: provenance, norms, cosines at the steering layer")
for b, t in P:
    bl = {c: torch.load(f"out/vectors/v_{t}_{b}_{c}.pt", map_location="cpu") for c in ("B1","B2","CONTROL")}
    v = {c: bl[c]["vectors"][L[t]].float() for c in bl}
    cos = lambda a, c: float(torch.nn.functional.cosine_similarity(v[a].flatten(), v[c].flatten(), dim=0))
    keys = sorted(k for k in bl["B1"].keys() if k not in ("vectors",))
    print(f"   {b:26s} {t}: |B1|={v['B1'].norm():.1f} |B2|={v['B2'].norm():.1f} |CTRL|={v['CONTROL'].norm():.1f}  cos(B1,B2)={cos('B1','B2'):+.2f} cos(B1,CTRL)={cos('B1','CONTROL'):+.2f} cos(B2,CTRL)={cos('B2','CONTROL'):+.2f}  keys={keys}")
    for c in bl:
        for k in ("skill_sha","skill","source","meta"):
            if k in bl[c]: print("      ", c, k, str(bl[c][k])[:80])
# cross-skill check: products 8B vs 14B skill files differ, and vectors were built after the skill files were written
for t in ("qwen3-8b","qwen3-14b"):
    for b in ("products","decimal_arithmetic","polynomial_multiplication","word_sorting"):
        f = os.path.expanduser(f"~/rg_gepa/gepa/{t}/{b}/skill.md")
        vf = f"out/vectors/v_{t}_{b}_B1.pt"
        if os.path.exists(vf): print(f"   skill {t}/{b}: sha={hashlib.md5(open(f,'rb').read()).hexdigest()[:8]} skill_mtime<vector_mtime={os.path.getmtime(f) < os.path.getmtime(vf)}")
