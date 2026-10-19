"""LiveMath: baseline vs Adilet's skill vs SkillOpt's released skill vs our skill, each with/without the meta rule.

    .plotvenv/bin/python src/make_skill_compare_table_png.py   -> results_table_skill_compare.png

All vLLM, greedy, same prompt/forcing/budgets. Evaluated on 556 = 608 minus SkillOpt's 52 train+val,
so no column was tuned on the questions it is scored on (SkillOpt's skill saw those 52).
livemath_ts never had a meta rule; livemath_ts_meta adds SkillOpt's two meta bullets verbatim.
placebo_livemath_ts is a length-matched (455 vs 450 tokens) text with no procedure: the control for ours.
"""
from __future__ import annotations

import collections
import glob
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "skill_search", "skillopt"))
from src.make_meta_split_table_png import render  # noqa: E402
import analyze as A  # noqa: E402

CONDS = {"baseline": "baseline\n(no skill)",
         "strength_audit": "Adilet's skill",
         "strength_audit_nometa": "Adilet's skill\nminus meta rule",
         "skillopt_full": "SkillOpt skill\n(GPT-5.5, released)",
         "skillopt_nometa": "SkillOpt skill\nminus meta rule",
         "livemath_ts_meta": "our skill\n+ SkillOpt's\nmeta rule",
         "livemath_ts": "our skill\n(livemath_ts,\nno meta rule)",
         "placebo_livemath_ts": "placebo text\n(no procedure,\nlength of ours)"}
SUBSETS = [("all", "556 questions", "main"),
           ("OTHER", "no meta option", "main:OTHER"),
           ("META", "meta option present (always correct)", "main:META")]


def mcnemar(a, b):
    b01 = sum(1 for i in a if not a[i] and b[i])
    b10 = sum(1 for i in a if a[i] and not b[i])
    n = b01 + b10
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(min(b01, b10) + 1)) / 2 ** n) if n else 1.0


def write_markdown(rows, cols, out):
    """Same numbers as the PNG, as a markdown table (for skills/README.md)."""
    lines = ["| model | subset | n | " + " | ".join(CONDS[c].replace("\n", " ") for c in cols) + " |",
             "|---|---|---|" + "---|" * len(cols)]
    for m, name, _, cells in rows:
        base = cells["baseline"]
        n = len(base)
        acc = {c: 100 * sum(cells[c].values()) / n for c in cols}
        txt = [f"{acc['baseline']:.1f}"]
        for c in cols[1:]:
            star = "*" if mcnemar(base, cells[c]) < 0.05 else ""
            txt.append(f"{acc[c]:.1f} ({acc[c] - acc['baseline']:+.1f}{star})")
        lines.append(f"| {m} | {name} | {n} | " + " | ".join(txt) + " |")
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote", out)


def main():
    cells = collections.defaultdict(dict)
    for d in ("full", "skillopt", "ts"):
        for p in glob.glob(os.path.join(ROOT, "results_vllm", d, "*.json")):
            b = json.load(open(p))
            s = b["summary"]
            if s["condition"] in CONDS:
                for r in b["records"]:
                    cells[(s["model_tag"], s["condition"])][r["id"]] = bool(r["em"])
    cols = list(CONDS)
    rows = []
    for m in A.MODELS:
        bad = [(c, len(cells.get((m, c), {}))) for c in cols if len(cells.get((m, c), {})) != 608]
        if bad:
            print(f"skip {m}: {bad}")
            continue
        for name, desc, key in SUBSETS:
            ids = A.SUBSETS[key]
            rows.append((m, name, desc, {c: {i: cells[(m, c)][i] for i in ids} for c in cols}))
    write_markdown(rows, cols, os.path.join(ROOT, "record", "tables", "skill_compare.md"))
    render(rows, cols, CONDS, "LiveMath: which skills help, with and without the meta-option rule (vLLM, greedy)",
           ["556 = our 608 minus the 52 questions SkillOpt's optimizer trained on. META = the option 'one of the "
            "remaining options is correct, but a stronger result can be proven', which is always correct.",
            "minus meta rule = only the bullets about that option removed; our skill + meta rule = SkillOpt's two bullets added. Budgets 2048 (8B/14B) / 4096 (27B), "
            "thinking off, answer forcing."],
           25, os.path.join(ROOT, "results_table_skill_compare.png"))


if __name__ == "__main__":
    main()
