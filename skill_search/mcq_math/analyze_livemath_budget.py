"""LiveMath 556 at two token budgets: per condition, META / OTHER / OTHER-centroid-wrong, paired vs baseline,
and each skill vs its own placebo. Usage: python analyze_livemath_budget.py results_2048 results_4096"""
import json, math, os, sys
CONDS = ["baseline", "placebo_matched", "strength_audit", "placebo_livemath_ts", "livemath_ts"]
def mcn(a, b, I):
    up = sum(1 for i in I if not a[i]["em"] and b[i]["em"]); dn = sum(1 for i in I if a[i]["em"] and not b[i]["em"]); n = up + dn
    p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, k) for k in range(min(up, dn) + 1)) / 2 ** n); return up, dn, p
for d in sys.argv[1:]:
    R = {}
    for c in CONDS:
        f = os.path.join(d, f"livemath556_qwen3-8b_{c}.json")
        if os.path.exists(f):
            b = json.load(open(f)); R[c] = ({r["id"]: r for r in b["records"]}, b["summary"])
    if "baseline" not in R: continue
    B = R["baseline"][0]; ids = list(B)
    groups = {"all": ids, "OTHER": [i for i in ids if B[i]["source"] == "OTHER"], "META": [i for i in ids if B[i]["source"] == "META"],
              "OTHER-cw": [i for i in ids if B[i]["source"] == "OTHER" and not B[i]["centroid_right"]]}
    print(f"\n== {d}   n={len(ids)}  (OTHER {len(groups['OTHER'])}, META {len(groups['META'])}, OTHER centroid-wrong {len(groups['OTHER-cw'])})")
    for c in CONDS:
        if c not in R: continue
        X, s = R[c]; cells = []
        for g, I in groups.items():
            acc = 100 * sum(X[i]["em"] for i in I) / len(I)
            if c == "baseline": cells.append(f"{g} {acc:5.1f}")
            else:
                u, dn, p = mcn(B, X, I); cells.append(f"{g} {acc:5.1f}{'*' if p < .05 else ' '}(+{u}/-{dn} p={p:.2g})")
        ln = sum(len(r["raw"]) for r in X.values()) / len(X)
        print(f"  {c:20s} forced {s['forced']:3d}  len {ln:5.0f} | " + " | ".join(cells))
    for sk, pl in [("livemath_ts", "placebo_livemath_ts"), ("strength_audit", "placebo_matched")]:
        if sk in R and pl in R:
            out = []
            for g in ("all", "OTHER", "META"):
                u, dn, p = mcn(R[pl][0], R[sk][0], groups[g]); out.append(f"{g} +{u}/-{dn} p={p:.2g}")
            print(f"  {sk} vs {pl}: " + " | ".join(out))
