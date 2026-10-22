"""PROTOCOL.md's selection rule and final report, for SkillOpt drafts on MCQ math.

SkillOpt is only the draft generator here: its accepted skills (and the seed) are the
drafts. Selection is PROTOCOL.md's, fixed in advance and run on dev only:

  * choose the draft with the highest mean dev accuracy gain over baseline,
    averaged over the three models (Qwen3-8B, Qwen3-14B, Qwen3.6-27B);
  * disqualify a draft whose mean gain on centroid-WRONG dev questions is more than
    3 points below its gain on centroid-right ones AND whose dev gain comes only
    from centroid-right items (gain on centroid-wrong <= 0): that pattern is the
    shortcut, not the maths;
  * ties -> the shorter skill.

    python protocol_select.py select <results dir> <bench> <drafts dir> <out chosen.md>
    python protocol_select.py report <results dir> <bench>

Results files are evaluate_vllm_mcq.py outputs: <bench>_<model tag>_<skill>_{dev,test}.json.
"""
from __future__ import annotations

import glob
import json
import math
import os
import shutil
import sys

MODELS = ["qwen3-8b", "qwen3-14b", "qwen3.6-27b"]
TEST_CONDS = ["placebo_matched", "strength_audit", "strength_audit_nometa",
              "placebo_livemath_ts", "livemath_ts", "chosen"]
PAIRS = [("strength_audit", "placebo_matched"), ("strength_audit_nometa", "placebo_matched"),
         ("livemath_ts", "placebo_livemath_ts"), ("chosen", "placebo_matched")]


def load(d, bench, model, name, split):
    f = os.path.join(d, f"{bench}_{model}_{name}_{split}.json")
    if not os.path.exists(f):
        return None
    return {r["id"]: r for r in json.load(open(f))["records"]}


def acc(recs, ids):
    return 100.0 * sum(recs[i]["em"] for i in ids) / len(ids) if ids else float("nan")


def mcnemar(a, b, ids):
    up = sum(1 for i in ids if not a[i]["em"] and b[i]["em"])
    down = sum(1 for i in ids if a[i]["em"] and not b[i]["em"])
    n = up + down
    p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, k) for k in range(min(up, down) + 1)) / 2 ** n)
    return up, down, p


def select(d, bench, drafts_dir, out):
    drafts = sorted(os.path.basename(f)[:-3] for f in glob.glob(os.path.join(drafts_dir, "*.md")))
    rows = []
    for dr in drafts:
        g_all, g_cw, g_cr, used = [], [], [], []
        for m in MODELS:
            base, rec = load(d, bench, m, "baseline", "dev"), load(d, bench, m, dr, "dev")
            if base is None or rec is None:
                continue
            ids = list(base)
            cw = [i for i in ids if not base[i]["centroid_right"]]
            cr = [i for i in ids if base[i]["centroid_right"]]
            g_all.append(acc(rec, ids) - acc(base, ids))
            g_cw.append(acc(rec, cw) - acc(base, cw))
            if cr:
                g_cr.append(acc(rec, cr) - acc(base, cr))
            used.append(m)
        if not used:
            continue
        mean = lambda v: sum(v) / len(v) if v else 0.0
        a, w, r = mean(g_all), mean(g_cw), mean(g_cr)
        disq = bool(g_cr) and (w < r - 3) and (w <= 0) and (a > 0)
        length = len(open(os.path.join(drafts_dir, dr + ".md")).read())
        rows.append({"draft": dr, "models": used, "dev_gain": a, "gain_centroid_wrong": w,
                     "gain_centroid_right": r, "disqualified": disq, "chars": length})
    print(f"\n== {bench}: dev selection (gain in points vs baseline, mean over {MODELS})")
    for x in rows:
        print(f"  {x['draft']:28s} gain {x['dev_gain']:+6.2f}  cw {x['gain_centroid_wrong']:+6.2f}  "
              f"cr {x['gain_centroid_right']:+6.2f}  {x['chars']:5d} chars  models={len(x['models'])}"
              f"{'  DISQUALIFIED' if x['disqualified'] else ''}")
    ok = [x for x in rows if not x["disqualified"] and len(x["models"]) == len(MODELS)]
    if not ok:
        sys.exit(f"no eligible draft for {bench} (every draft disqualified or missing a model)")
    best = sorted(ok, key=lambda x: (-round(x["dev_gain"], 6), x["chars"]))[0]
    shutil.copy(os.path.join(drafts_dir, best["draft"] + ".md"), out)
    json.dump({"chosen": best, "all": rows}, open(out.replace(".md", "_selection.json"), "w"), indent=1)
    print(f"  -> chosen: {best['draft']} (dev gain {best['dev_gain']:+.2f}) -> {out}")


def report(d, bench):
    print(f"\n== {bench}: TEST (touched once), paired exact McNemar vs baseline")
    for m in MODELS:
        base = load(d, bench, m, "baseline", "test")
        if base is None:
            continue
        ids = list(base)
        groups = {"all": ids, "centroid-wrong": [i for i in ids if not base[i]["centroid_right"]],
                  "centroid-right": [i for i in ids if base[i]["centroid_right"]]}
        print(f"  -- {m}  n={len(ids)}  (centroid-right {len(groups['centroid-right'])})")
        print(f"    {'baseline':22s} " + " | ".join(f"{g} {acc(base, I):5.1f}" for g, I in groups.items() if I))
        res = {"baseline": base}
        for c in TEST_CONDS:
            rec = load(d, bench, m, c, "test")
            if rec is None:          # not every condition applies to every benchmark (livemath_ts is MCQ-only)
                continue
            res[c] = rec
            cells = []
            for g, I in groups.items():
                if I:
                    u, dn, p = mcnemar(base, rec, I)
                    cells.append(f"{g} {acc(rec, I):5.1f}{'*' if p < 0.05 else ' '}(+{u}/-{dn} p={p:.2g})")
            print(f"    {c:22s} " + " | ".join(cells))
        for sk, pl in PAIRS:
            if sk in res and pl in res:
                u, dn, p = mcnemar(res[pl], res[sk], ids)
                print(f"    {sk} vs {pl}: +{u}/-{dn} p={p:.2g}")


if __name__ == "__main__":
    if sys.argv[1] == "select":
        select(*sys.argv[2:6])
    else:
        report(*sys.argv[2:4])
