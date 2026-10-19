"""Score the SkillOpt LiveMath cells.

    python skill_search/skillopt/analyze.py            # prints markdown, writes results.csv

Two engines, each compared only with its own baseline:
  HF transformers (results/):        baseline, TS full, three ES arms   (8B, 27B)
  vLLM (results_vllm/full, /skillopt): baseline, placebo_matched, TS full / nometa,
                                       the two length-matched placebos   (8B, 14B, 27B)

Subsets: main = our 608 minus SkillOpt's 52 train+val items; so_test = their 125
test items; trainval = the 52 (contamination check only); clean = months they
never saw (202603+). Each is also split META / OTHER (META = the "a stronger
result can be proven" option is present, and it is then always correct).
"""
from __future__ import annotations

import collections
import csv
import glob
import json
import math
import os
import re

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
META_RE = re.compile(r"stronger result can be proven|one of the (remaining|other) options", re.I)
MODELS = ["qwen3-8b", "qwen3-14b", "qwen3.6-27b"]

ROWS = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(KIT, "data", "livemath.jsonl"))}
META_LETTER = {}
for qid, r in ROWS.items():
    hit = [i for i, o in enumerate(r["options"]) if META_RE.search(o)]
    if hit:
        META_LETTER[qid] = "ABCDE"[hit[0]]
TV = set(json.load(open(os.path.join(KIT, "skill_search", "ids_skillopt_trainval.json"))))
TEST = set(json.load(open(os.path.join(KIT, "skill_search", "ids_skillopt_test.json"))))
ALL = set(ROWS)
SUBSETS = {"main": ALL - TV, "so_test": TEST, "trainval": TV,
           "clean": {q for q in ALL if ROWS[q]["month"] >= "202603"}}
for k in list(SUBSETS):
    SUBSETS[k + ":META"] = SUBSETS[k] & set(META_LETTER)
    SUBSETS[k + ":OTHER"] = SUBSETS[k] - set(META_LETTER)

HF_CELLS = {"baseline": "baseline", "text_skillopt_full": "TS full",
            "embed_v_{t}_skillopt_full_lmtv_n50_placebo": "ES vs-dummy",
            "embed_v_{t}_skillopt_full_lmtv_n50_plain": "ES vs-nothing",
            "embed_v_{t}_placebo_skillopt_full_lmtv_n50_plain": "placebo vector"}
VLLM_CELLS = {"baseline": "baseline", "placebo_matched": "placebo (kit, 309 tok)",
              "skillopt_full": "TS full", "skillopt_nometa": "TS nometa",
              "placebo_skillopt_full": "placebo, len-matched full",
              "placebo_skillopt_nometa": "placebo, len-matched nometa"}


def parse(raw):
    """src/evaluate.parse_livemath, copied so this runs without torch."""
    m = re.findall(r"Answer:\s*\**\(?([A-E])\b", raw, re.I)
    if m:
        return m[-1].upper()
    for line in reversed([l.strip() for l in raw.strip().split("\n") if l.strip()]):
        m = re.fullmatch(r"\**\(?([A-E])\)?\.?\**", line, re.I)
        if m:
            return m.group(1).upper()
    return None


def mcnemar(a, b, ids):
    b01 = sum(1 for i in ids if not a[i]["em"] and b[i]["em"])
    b10 = sum(1 for i in ids if a[i]["em"] and not b[i]["em"])
    n = b01 + b10
    if not n:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(min(b01, b10) + 1)) / 2 ** n)


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    out, run = [0.0] * len(ps), 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - r) * ps[i]))
        out[i] = run
    return out


def load_hf():
    cells = collections.defaultdict(dict)
    for p in glob.glob(os.path.join(KIT, "results", "livemath_*.json")):
        b = json.load(open(p))
        t = b["summary"]["model_tag"]
        stem = re.sub(rf"^livemath_{re.escape(t)}_|_s\d+of\d+$", "", os.path.basename(p)[:-5])
        stem = re.sub(r"_L\d+_g[\d.]+$", "", stem)
        for k, lab in HF_CELLS.items():
            if stem == k.format(t=t):
                b["summary"]["path"] = p
                for r in b["records"]:
                    cells[(t, lab)][r["id"]] = dict(r, _s=b["summary"])
    return cells


def load_vllm():
    cells = collections.defaultdict(dict)
    for d in ("full", "skillopt"):
        for p in glob.glob(os.path.join(KIT, "results_vllm", d, "*.json")):
            b = json.load(open(p))
            s = b["summary"]
            lab = VLLM_CELLS.get(s["condition"])
            if lab:
                for r in b["records"]:
                    cells[(s["model_tag"], lab)][r["id"]] = dict(r, _s=s)
    return cells


def forced(r):
    s = r["_s"]
    # vLLM records carry gen_tokens; HF records do not, so use the shard summary rate
    if "gen_tokens" in r:
        return r["gen_tokens"] >= s["max_new_tokens"]
    return None


def table(engine, cells, labels, ts_vs):
    out = []
    print(f"\n## {engine}\n")
    for t in MODELS:
        if (t, "baseline") not in cells:
            continue
        base = cells[(t, "baseline")]
        conds = [l for l in labels if (t, l) in cells and len(cells[(t, l)]) == 608]
        missing = [l for l in labels if (t, l) in cells and len(cells[(t, l)]) != 608]
        print(f"### {t}" + (f"   (incomplete, skipped: {', '.join(f'{m} n={len(cells[(t, m)])}' for m in missing)})"
                            if missing else ""))
        # Holm family on the main subset: every condition vs baseline + TS vs each ES arm
        fam = [(c, "baseline") for c in conds if c != "baseline"] + \
              [(a, b) for a, b in ts_vs if a in conds and b in conds]
        praw = [mcnemar(cells[(t, b)], cells[(t, a)], SUBSETS["main"]) for a, b in fam]
        padj = dict(zip(fam, holm(praw)))
        hdr = ["subset", "n"] + conds
        print("| " + " | ".join(hdr) + " |\n|" + "---|" * len(hdr))
        for sname in ["main", "main:OTHER", "main:META", "clean", "so_test", "so_test:OTHER",
                      "so_test:META", "trainval", "trainval:META"]:
            ids = SUBSETS[sname]
            b_acc = 100 * sum(base[i]["em"] for i in ids) / len(ids)
            cells_txt = []
            for c in conds:
                acc = 100 * sum(cells[(t, c)][i]["em"] for i in ids) / len(ids)
                if c == "baseline":
                    cells_txt.append(f"{acc:.1f}")
                    continue
                p = mcnemar(base, cells[(t, c)], ids)
                star = "*" if p < 0.05 else ""
                cells_txt.append(f"{acc:.1f} ({acc - b_acc:+.1f}{star})")
                out.append(dict(engine=engine, model=t, subset=sname, n=len(ids), cond=c, acc=round(acc, 2),
                                delta=round(acc - b_acc, 2), p_vs_base=p,
                                p_holm=padj.get((c, "baseline")) if sname == "main" else ""))
            print(f"| {sname} | {len(ids)} | " + " | ".join(cells_txt) + " |")
        out.append(dict(engine=engine, model=t, subset="main", n=len(SUBSETS["main"]), cond="baseline",
                        acc=round(100 * sum(base[i]["em"] for i in SUBSETS["main"]) / len(SUBSETS["main"]), 2)))
        print("\nMain subset, Holm-adjusted (family of %d): " % len(fam) +
              "; ".join(f"{a} vs {b}: p={padj[(a, b)]:.3g} (raw {p:.3g})" for (a, b), p in zip(fam, praw)))
        meta_ids = SUBSETS["main:META"]
        diag = []
        for c in conds:
            recs = cells[(t, c)]
            pick = sum(parse(recs[i]["raw"]) == META_LETTER[i] for i in meta_ids) / len(meta_ids)
            ids = SUBSETS["main"]
            prate = sum(parse(recs[i]["raw"]) is not None for i in ids) / len(ids)
            fr = [forced(recs[i]) for i in ids]
            if fr[0] is None:   # HF: shard-level counts
                shards = {id(recs[i]["_s"]): recs[i]["_s"] for i in recs}.values()
                frate = sum(s["forced"] for s in shards) / sum(s["n"] for s in shards)
            else:
                frate = sum(fr) / len(fr)
            diag.append(f"{c}: META-pick {100 * pick:.1f}%, parse {100 * prate:.1f}%, capped {100 * frate:.1f}%")
            for row in out:
                if row["model"] == t and row["engine"] == engine and row["cond"] == c and row["subset"] == "main":
                    row.update(meta_pick=round(100 * pick, 1), parse=round(100 * prate, 1), capped=round(100 * frate, 1))
        print("Diagnostics (main; META-pick = share of META questions where the META option was chosen; "
              "it is always correct, so precision is 100% by construction):\n  " + "\n  ".join(diag) + "\n")
    return out


def main():
    print(f"Subsets: main {len(SUBSETS['main'])} (META {len(SUBSETS['main:META'])}), so_test {len(TEST)} "
          f"(META {len(SUBSETS['so_test:META'])}), trainval {len(TV)} (META {len(SUBSETS['trainval:META'])}), "
          f"clean {len(SUBSETS['clean'])}. META base rate on main: "
          f"{100 * len(SUBSETS['main:META']) / len(SUBSETS['main']):.1f}%. Cells: acc (delta vs baseline, * p<.05 McNemar).")
    rows = table("HF transformers (same settings as results/)", load_hf(), list(HF_CELLS.values()),
                 [("TS full", "ES vs-dummy"), ("TS full", "ES vs-nothing"), ("TS full", "placebo vector")])
    rows += table("vLLM text arms", load_vllm(), list(VLLM_CELLS.values()),
                  [("TS full", "TS nometa"), ("TS full", "placebo, len-matched full"),
                   ("TS nometa", "placebo, len-matched nometa")])
    keys = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k) if k in rows[0] else 99)
    with open(os.path.join(HERE, "results.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
