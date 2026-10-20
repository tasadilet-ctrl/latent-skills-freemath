"""Math skills off LiveMath: OfficeQA (text-only, cited pages) and SpreadsheetBench (single-turn).

    .plotvenv/bin/python src/make_transfer_table_png.py livemath_ts [more skill stems...]
        -> results_table_transfer_<stem>.png and record/tables/transfer_<stem>.md, per skill

Columns: baseline, the skill as text, the skill as a steering vector extracted against
a length-matched placebo, and against no system prompt (neutral pool, n=50; 8B L34,
14B L37, 27B L62, gamma 0.3 relative). Each benchmark against its own baseline.
"""
from __future__ import annotations

import collections
import glob
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.make_meta_split_table_png import render  # noqa: E402

MODELS = ["qwen3-4b", "qwen3-8b", "qwen3-14b", "qwen3.6-27b"]
BENCH = {"officeqa": ("OfficeQA", "text-only: question + cited pages"),
         "spreadsheet": ("SpreadsheetBench", "single-turn")}
N_EXPECT = {"officeqa": 238, "spreadsheet": 398}


def load(stem):
    """{(model, bench, col): {id: bool}} from results/ shards."""
    cells = collections.defaultdict(dict)
    for bench in BENCH:
        for p in glob.glob(os.path.join(ROOT, "results", f"{bench}_*_s*of*.json")):
            b = json.load(open(p))
            s = b["summary"]
            t = s["model_tag"]
            name = re.sub(r"_s\d+of\d+$", "", os.path.basename(p)[:-5])
            rest = name[len(f"{bench}_{t}_"):]
            col = {"baseline": "baseline", f"text_{stem}": "text"}.get(rest)
            m = re.fullmatch(rf"embed_v_{re.escape(t)}_{re.escape(stem)}_neutral_n50_(placebo|plain)_L\d+_g0\.3", rest)
            if m:
                col = {"placebo": "ES vs placebo", "plain": "ES vs nothing"}[m.group(1)]
            if col:
                for r in b["records"]:
                    cells[(t, bench, col)][r["id"]] = bool(r["em"])
    return cells


def mcnemar(a, b):
    b01 = sum(1 for i in a if not a[i] and b[i])
    b10 = sum(1 for i in a if a[i] and not b[i])
    n = b01 + b10
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(min(b01, b10) + 1)) / 2 ** n) if n else 1.0


def main():
    cols = ["baseline", "text", "ES vs placebo", "ES vs nothing"]
    for stem in sys.argv[1:] or ["livemath_ts"]:
        cells = load(stem)
        pretty = {"baseline": "baseline\n(no skill)", "text": f"{stem}\nas text",
                  "ES vs placebo": "vector:\nskill - placebo", "ES vs nothing": "vector:\nskill - nothing"}
        rows, md = [], ["| model | benchmark | n | " + " | ".join(cols) + " |", "|---|---|---|" + "---|" * len(cols)]
        for m in MODELS:
            for bench, (bname, desc) in BENCH.items():
                have = [c for c in cols if len(cells.get((m, bench, c), {})) == N_EXPECT[bench]]
                if "baseline" not in have or len(have) < 2:
                    print(f"skip {m} {bench}: {[(c, len(cells.get((m, bench, c), {}))) for c in cols]}")
                    continue
                missing = [c for c in cols if c not in have]
                if missing:
                    print(f"{m} {bench}: incomplete {missing}")
                ids = sorted(cells[(m, bench, "baseline")], key=str)
                full = {c: ({i: cells[(m, bench, c)][i] for i in ids} if c in have else None) for c in cols}
                if missing:     # render() needs every column; leave the row out until complete
                    continue
                rows.append((m, bname, desc, full))
                base = full["baseline"]
                acc = {c: 100 * sum(full[c].values()) / len(ids) for c in cols}
                txt = [f"{acc['baseline']:.1f}"] + [
                    f"{acc[c]:.1f} ({acc[c] - acc['baseline']:+.1f}{'*' if mcnemar(base, full[c]) < 0.05 else ''})"
                    for c in cols[1:]]
                md.append(f"| {m} | {bname} | {len(ids)} | " + " | ".join(txt) + " |")
        os.makedirs(os.path.join(ROOT, "record", "tables"), exist_ok=True)
        with open(os.path.join(ROOT, "record", "tables", f"transfer_{stem}.md"), "w") as f:
            f.write("\n".join(md) + "\n")
        if rows:
            render(rows, cols, pretty, f"Math skill {stem} off LiveMath: OfficeQA and SpreadsheetBench",
                   ["OfficeQA: 238 questions, cited bulletin pages in the prompt, numeric answer within the "
                    "manifest tolerance. SpreadsheetBench: 398 tasks, one turn, graded on the output file.",
                    "vectors: neutral prompt pool, n=50; 4B and 8B layer 34, 14B 37, 27B 62; gamma 0.3 relative. "
                    "Greedy, thinking off."],
                   15, os.path.join(ROOT, f"results_table_transfer_{stem}.png"))
        print("\n".join(md))


if __name__ == "__main__":
    main()
