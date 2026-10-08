"""One table across every axis: benchmark x harness x model x condition.

Columns are the four conditions the study compares, plus the control that
turned out to matter most:

  baseline      no skill
  text          skill as text in the prompt
  embed/dummy   vector = E[h|skill] - E[h|placebo]     (procedure isolated)
  embed/none    vector = E[h|skill] - E[h|no prompt]   (procedure + prompt-presence)
  CONTROL       vector = E[h|placebo] - E[h|no prompt] (NO SKILL AT ALL)

The CONTROL column is the point of the whole table. If it matches or beats
embed/none, the gain is not skill transfer.

Rows separate the HARNESS as well as the benchmark, because SpreadsheetBench
was run two ways -- a full OpenHands agent and a single-turn code-generation
variant -- and they are not the same task.
"""
from __future__ import annotations

import glob
import json
import math
import os
import re
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

COLS = ["baseline", "text", "embed/dummy", "embed/none", "CONTROL"]


def wilson(k, n, z=1.96):
    if not n:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def mcnemar(a, b):
    sh = set(a) & set(b)
    b01 = sum(1 for i in sh if not a[i] and b[i])
    b10 = sum(1 for i in sh if a[i] and not b[i])
    n = b01 + b10
    if not n:
        return 1.0
    lo = min(b01, b10)
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(lo + 1)) / 2 ** n)


def classify(s):
    """(benchmark, harness, model, condition) or None to skip."""
    dom = s.get("domain", "")
    cond = s.get("condition")
    tag = s.get("model_tag") or s.get("model", "?").split("/")[-1].lower()

    if dom == "spreadsheet_agent":
        bench, harness = "SpreadsheetBench", "agent"
    elif dom == "spreadsheet":
        bench, harness = "SpreadsheetBench", "single-turn"
    elif dom == "livemath":
        bench, harness = "LiveMath", "direct"
    elif dom in ("gsm8k", "hotpotqa"):
        return None                      # pre-study pilot, different protocol
    elif dom.startswith("officeqa"):
        bench, harness = "OfficeQA", "agent"
    else:
        bench, harness = dom, "direct"

    # The agent SDK is part of the condition, not an implementation detail:
    # OpenHands and Strands do not give the model the same tools, names or
    # error text, so their cells are not comparable and must not merge into
    # one row. Runs predating 2026-10-05 carry no "harness" key and are
    # OpenHands by definition.
    if harness == "agent":
        harness = s.get("harness") or "openhands"

    if cond == "baseline":
        col = "baseline"
    elif cond == "text":
        # Each benchmark has ONE canonical skill, and that is its "text" arm.
        # Anything else is an ablation and keeps its own column, because
        # merging two different interventions into one cell produces a number
        # true of neither.
        #
        # Before 2026-10-05 only LiveMath's skill was recognised here, so
        # SpreadsheetBench's spreadsheet_edit landed in "text:edit" and
        # OfficeQA's officeqa_lookup in "text:lookup", leaving the "text"
        # column empty on those rows. src/make_table_png.py already treated
        # them as the text arm, so the table and the PNG disagreed. CANON
        # fixes matrix.py to match. No accuracy number changes -- only which
        # column a cell is printed in.
        #
        # LiveMath's canonical skill is strength_audit since 2026-10-05.
        # compare_claims (v1-v3) is archived and keeps its own columns
        # ("text:claims", "text:v3", "text:v2") -- it must NOT share the
        # "text" column with strength_audit, or two different interventions
        # merge into one cell.
        CANON = {"strength_audit", "spreadsheet_edit",
                 "officeqa_lookup", "decompose_verify"}
        sk = (s.get("skill") or "").replace(".md", "")
        col = "text" if (not sk or sk in CANON) else "text:" + sk.split("_")[-1]
        if s.get("skill_position") == "user":
            col += "@usr"
    elif cond == "embed":
        f = (s.get("vector") or {}).get("file", "")
        skill_is_placebo = "placebo_matched_" in f or f.startswith("v_") and "_placebo_matched" in f
        # the CONTROL is a vector whose SOURCE SKILL is the placebo itself
        body = re.sub(r"^v_[^_]+_", "", f.replace(".pt", ""))
        src = body.split("_livemath")[0].split("_spreadsheet")[0].split("_neutral")[0]
        if src.startswith("placebo"):
            col = "CONTROL"
        elif f.endswith("_placebo.pt"):
            col = "embed/dummy"
        else:
            col = "embed/none"
        if "_usr_" in f:
            col += "@usr"
    else:
        return None
    return bench, harness, tag, col


def main():
    cells = defaultdict(lambda: {"items": {}, "n": 0})
    for path in sorted(glob.glob(os.path.join(ROOT, "results", "*.json"))):
        try:
            blob = json.load(open(path))
        except Exception:
            continue
        if "summary" not in blob or "records" not in blob:
            continue
        s = blob["summary"]
        key = classify(s)
        if not key:
            continue
        if "pilot" in os.path.basename(path) or "fixpilot" in os.path.basename(path):
            continue
        c = cells[key]
        for r in blob["records"]:
            c["items"][r["id"]] = r["em"]

    if not cells:
        print("no results"); return

    order = {"LiveMath": 0, "SpreadsheetBench": 1, "OfficeQA": 2}
    msize = {"qwen3-8b": 8, "qwen3-14b": 14, "qwen3.6-27b": 27}
    rows = sorted({(b, h, m) for b, h, m, _ in cells},
                  key=lambda x: (order.get(x[0], 9), x[1], msize.get(x[2], 99)))
    allcols = COLS + [c + "@usr" for c in ("text", "embed/dummy", "embed/none", "CONTROL")]
    extra = sorted({c for _, _, _, c in cells if c not in allcols})
    allcols = COLS[:2] + extra + COLS[2:] + [c + "@usr" for c in
              ("text", "embed/dummy", "embed/none", "CONTROL")]
    seen=set(); allcols=[c for c in allcols if not (c in seen or seen.add(c))]
    used = [c for c in allcols if any((b, h, m, c) in cells for b, h, m in rows)]
    # mark cells whose n is far below that row's largest -- partial/cancelled runs
    rowmax = {}
    for (bb, hh, mm, cc), v in cells.items():
        rowmax[(bb, hh, mm)] = max(rowmax.get((bb, hh, mm), 0), len(v["items"]))

    w = 46
    print()
    print("=" * (w + 13 * len(used)))
    print("ACCURACY %  (n)   --  '.' = not run")
    print("=" * (w + 13 * len(used)))
    print(f"{'benchmark / harness / model':<{w}}" + "".join(f"{c:>13}" for c in used))
    print("-" * (w + 13 * len(used)))
    for b, h, m in rows:
        lbl = f"{b} [{h}] {m}"
        line = f"{lbl:<{w}}"
        for c in used:
            cell = cells.get((b, h, m, c))
            if not cell or not cell["items"]:
                line += f"{'.':>13}"
            else:
                it = cell["items"]
                partial = "!" if len(it) < 0.9 * rowmax[(b, h, m)] else " "
                line += f"{sum(it.values())/len(it)*100:>7.1f}({len(it):>3}){partial}"
        print(line)

    # deltas vs that row's own baseline, with paired tests
    print()
    print("=" * (w + 13 * len(used)))
    print("DELTA vs that row's baseline   (McNemar p in brackets)")
    print("=" * (w + 13 * len(used)))
    print(f"{'benchmark / harness / model':<{w}}" + "".join(f"{c:>13}" for c in used if c != "baseline"))
    print("-" * (w + 13 * len(used)))
    for b, h, m in rows:
        base = cells.get((b, h, m, "baseline"), {}).get("items", {})
        line = f"{f'{b} [{h}] {m}':<{w}}"
        for c in used:
            if c == "baseline":
                continue
            cell = cells.get((b, h, m, c))
            if not cell or not cell["items"] or not base:
                line += f"{'.':>13}"
            else:
                it = cell["items"]
                d = sum(it.values())/len(it) - sum(base.values())/len(base)
                p = mcnemar(base, it)
                star = "*" if p < 0.05 else " "
                line += f"{d*100:>+7.1f}({p:.2f}){star}"
        print(line)
    print()
    print("!  = fewer items than the rest of that row (partial or cancelled run)")
    print("* p<0.05 uncorrected. With ~15 comparisons the Bonferroni threshold is ~0.003.")
    print("CONTROL = steering vector built from the DUMMY skill only, containing no")
    print("procedure. Where CONTROL matches or beats embed/none, the gain is not")
    print("skill transfer.")
    print()


if __name__ == "__main__":
    main()
