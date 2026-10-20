"""LiveMath: our skill vectors vs Rakhat's (branch rakhat/step-vector-pilot), skill livemath_ts.

    .plotvenv/bin/python src/make_rakhat_compare_table_png.py
        -> results_table_rakhat_compare.png and record/tables/rakhat_compare.md

Every column is the HF runner (src/evaluate.py), greedy, thinking off, answer forcing,
2048 new tokens (4B, 14B) / 4096 (27B). Scored on the 556 questions outside SkillOpt's
52 train+val; Rakhat's vectors were built from replies to those 52.
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "skill_search", "skillopt"))
from src.make_meta_split_table_png import render  # noqa: E402
from src.make_skill_compare_table_png import mcnemar  # noqa: E402
import analyze as A  # noqa: E402

MODELS = ["qwen3-4b", "qwen3-14b", "qwen3.6-27b"]
STEM = "livemath_ts"
COLS = {"baseline": "baseline\n(no skill)",
        "text": "our skill\nas text",
        "ours_placebo": "our vector:\nskill - placebo",
        "ours_plain": "our vector:\nskill - nothing",
        "replyA": "Rakhat reply A\n(same prompt,\nreply differs)",
        "replyB": "Rakhat reply B\n(+ skill in\ncontext)",
        "stepA": "Rakhat step A\n(at 'Answer:')",
        "stepB": "Rakhat step B\n(at 'Answer:',\n+ skill)"}
SUBSETS = [("all", "556 questions", "main"),
           ("OTHER", "no meta option", "main:OTHER"),
           ("META", "meta option present (always correct)", "main:META")]


def column(rest, tag):
    if rest == "baseline":
        return "baseline"
    if rest == f"text_{STEM}":
        return "text"
    m = re.fullmatch(rf"embed_v_{re.escape(tag)}_{STEM}_neutral_n50_(placebo|plain)_L\d+_g0\.3", rest)
    if m:
        return "ours_" + m.group(1)
    m = re.fullmatch(rf"(?:embed|step)_v_{re.escape(tag)}_{STEM}_(replyA|replyB|stepA|stepB)_L[\d-]+_[gm][\d.]+", rest)
    return m.group(1) if m else None


def main():
    cells = collections.defaultdict(dict)
    parsed = collections.defaultdict(lambda: [0.0, 0])           # (model, col) -> parsed, n
    for p in glob.glob(os.path.join(ROOT, "results", "livemath_*_s*of*.json")):
        b = json.load(open(p))
        t = b["summary"]["model_tag"]
        rest = re.sub(r"_s\d+of\d+$", "", os.path.basename(p)[:-5])[len(f"livemath_{t}_"):]
        c = column(rest, t)
        if c:
            cells[(t, c)].update({r["id"]: bool(r["em"]) for r in b["records"]})
            parsed[(t, c)][0] += b["summary"]["parse_rate"] * b["summary"]["n"]
            parsed[(t, c)][1] += b["summary"]["n"]
    cols = list(COLS)
    rows, md = [], ["| model | subset | n | " + " | ".join(COLS[c].replace("\n", " ") for c in cols) + " |",
                    "|---|---|---|" + "---|" * len(cols)]
    for m in MODELS:
        bad = [(c, len(cells.get((m, c), {}))) for c in cols if len(cells.get((m, c), {})) != 608]
        if bad:
            print(f"skip {m}: {bad}")
            continue
        for name, desc, key in SUBSETS:
            ids = A.SUBSETS[key]
            full = {c: {i: cells[(m, c)][i] for i in ids} for c in cols}
            rows.append((m, name, desc, full))
            base = full["baseline"]
            acc = {c: 100 * sum(full[c].values()) / len(ids) for c in cols}
            md.append(f"| {m} | {name} | {len(ids)} | {acc['baseline']:.1f} | " + " | ".join(
                f"{acc[c]:.1f} ({acc[c] - acc['baseline']:+.1f}{'*' if mcnemar(base, full[c]) < 0.05 else ''})"
                for c in cols[1:]) + " |")
    with open(os.path.join(ROOT, "record", "tables", "rakhat_compare.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))
    shown = {m for m, *_ in rows}
    broken = [f"{m} {COLS[c].split(chr(10))[0]} ({100 * k / n:.0f}%)" for (m, c), (k, n) in sorted(parsed.items())
              if m in shown and n and k / n < 0.9]
    if broken:
        print("parse rate < 90%:", broken)
    if rows:
        render(rows, cols, COLS, "LiveMath: our skill vectors vs Rakhat's (skill: livemath_ts)",
               ["556 = 608 minus SkillOpt's 52 train+val (Rakhat's vectors are built from replies to those 52). "
                "META = the 'stronger result can be proven' option, always correct.",
                "ours: last prompt token, neutral prompts, n=50, one layer (4B L34, 14B L37, 27B L62), gamma 0.3 relative. "
                "reply: mean over reply tokens, second half of layers, gamma 0.02 relative.",
                "step: state at the ':' of 'Answer:', added only there, 4B L32 / 14B L36 / 27B L57, strength 1.5. "
                "HF runner, greedy, thinking off, 2048 tokens (27B 4096)."]
               + (["Replies with a parseable answer below 90% (the vector broke the model at this strength, e.g. loops, "
                   "'Answer: <D>'): " + ", ".join(broken) + "."] if broken else []),
               15, os.path.join(ROOT, "results_table_rakhat_compare.png"))


if __name__ == "__main__":
    main()
