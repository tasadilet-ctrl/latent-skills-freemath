"""Score vector-arm replies with Reasoning Gym (run in ~/rg_env). usage: rescore_rg.py <out_dir>"""
import glob, json, math, os, re, sys, collections
import reasoning_gym as rg
D = sys.argv[1]; ANS = re.compile(r"<answer>(.*?)</answer>", re.S)
CONDS = ["baseline", "placebo", "text", "B1", "B2", "CONTROL"]
def mcn(a, b):
    up = sum(1 for i in a if not a[i] and b[i]); dn = sum(1 for i in a if a[i] and not b[i]); n = up + dn
    return up, dn, (1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, j) for j in range(min(up, dn) + 1)) / 2 ** n))
keys = sorted({tuple(os.path.basename(f).rsplit("_", 2)[0].rsplit("_", 1)) for f in glob.glob(f"{D}/results/*_test.json")})
import sympy
def poly_ok(pred, question):
    # polynomial_multiplication is not reproducible across processes: gold = expansion of the asked expression
    expr = question.split(":", 1)[1].split("\n", 1)[0].strip()
    try: return sympy.expand(sympy.sympify(pred.replace("^", "**")) - sympy.sympify(expr)) == 0
    except Exception: return False
for bench, tag in keys:
    ds = rg.create_dataset(bench, size=200, seed=0)
    items = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "items", f"{bench}_test.json")))
    ok, info = {}, {}
    for c in CONDS:
        f = f"{D}/results/{bench}_{tag}_{c}_test.json"
        if not os.path.exists(f): continue
        d = json.load(open(f)); ok[c] = {}
        for r in d["records"]:
            i = int(r["id"].rsplit("-", 1)[1]); m = ANS.findall(r["raw"])
            if bench == "polynomial_multiplication":
                ok[c][i] = bool(m) and poly_ok(m[-1].strip(), items[i]["question"]); continue
            try: s = float(ds.score_answer(m[-1].strip(), ds[i])) if m else 0.0
            except Exception: s = 0.0
            ok[c][i] = s >= 1.0
        info[c] = d["summary"]
    if "baseline" not in ok: continue
    print(f"\n== {bench}  {tag}  (HF engine, test n={len(ok['baseline'])}, Reasoning Gym scoring)")
    base = 100 * sum(ok["baseline"].values()) / len(ok["baseline"])
    for c in CONDS:
        if c not in ok: continue
        acc = 100 * sum(ok[c].values()) / len(ok[c]); s = info[c]
        ex = f"  chars={s['mean_chars']:.0f} forced={s['forced']}" + (f"  L{s['vector']['layer']} coh={s['vector']['coherence']:+.2f}" if s.get("vector") else "")
        if c == "baseline": print(f"  {c:9s} {acc:5.1f}{ex}"); continue
        up, dn, p = mcn(ok["baseline"], ok[c])
        print(f"  {c:9s} {acc:5.1f}{'*' if p < .05 else ' '} ({acc-base:+.1f}, +{up}/-{dn} p={p:.2g}){ex}")
    for x, y in (("text", "placebo"), ("B1", "CONTROL"), ("B2", "CONTROL"), ("B1", "text"), ("B2", "text")):
        if x in ok and y in ok:
            up, dn, p = mcn(ok[y], ok[x]); print(f"  {x} vs {y}: +{up}/-{dn} p={p:.2g}")
