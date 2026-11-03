"""Cells for make_math_skills_table.py, from the saved per-question test results (run on the box).

    python compute_math_skills_cells.py > math_skills_cells.json

MCQ: ~/mcq_math/protocol/<bench>/results_rescored (format-neutral parser).
Free-form: ~/skillopt_work/protocol_fm/<bench>/results_mv: the saved replies rescored with Math-Verify
installed (math_gepa/rescore_mv.py). The original results/ were scored by string match only, because
math_verify was missing from the run env and the scorer counted its ImportError as "wrong";
those cells are kept in math_skills_cells_stringonly.json.
"letters" counts free-form replies that answer with an option letter (A-J) although the
question has no options: livemath_ts tells the model to compare options, and the small models
then invent them. Every cell is paired with its row's baseline on identical items: exact two-sided McNemar.
"""
import json
import math
import os
import re

H = os.path.expanduser("~")
BENCHES = [("mmlupro_math_tq_sb", "MMLU-Pro math", "mcq", f"{H}/mcq_math/protocol/mmlupro_math_tq_sb/results_rescored"),
           ("supergpqa_math_hard", "SuperGPQA hard math", "mcq", f"{H}/mcq_math/protocol/supergpqa_math_hard/results_rescored")]
BENCHES += [(b, lab, "freeform", f"{H}/skillopt_work/protocol_fm/{b}/results_mv") for b, lab in
            [("beyondaime", "BeyondAIME"), ("hardmath2", "HARDMath2"), ("realmath", "RealMath"),
             ("imoanswer", "IMO-AnswerBench"), ("arxivmath", "ArxivMath")]]
MODELS = [("qwen3-8b", "Qwen 3 8b"), ("qwen3-14b", "Qwen 3 14b"), ("qwen3.6-27b", "Qwen 3.6 27b")]
# table column -> result-file condition name
COLS = {"baseline": "baseline", "placebo": "placebo_matched", "strength_audit": "strength_audit",
        "strength_audit_nometa": "strength_audit_nometa", "placebo_ts": "placebo_livemath_ts",
        "livemath_ts": "livemath_ts", "livemath_ts_meta": "livemath_ts_meta", "skill": "chosen"}


def load(d, b, m, c):
    f = os.path.join(d, f"{b}_{m}_{c}_test.json")
    return {r["id"]: r for r in json.load(open(f))["records"]} if os.path.exists(f) else None


LETTER = re.compile(r"\(?[A-J]\)?")


def letters(recs):
    """Free-form items answered with an option letter that does not exist (the MCQ skill's habit)."""
    return sum(1 for r in recs.values() if LETTER.fullmatch(str(r["pred"]).strip())
               and not LETTER.fullmatch(str(r["gold"]).strip()))


def mcnemar(a, b):
    up = sum(1 for i in a if not a[i] and b[i])
    dn = sum(1 for i in a if a[i] and not b[i])
    n = up + dn
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, k) for k in range(min(up, dn) + 1)) / 2 ** n)


rows = []
for b, lab, kind, d in BENCHES:
    for m, mlab in MODELS:
        raw = load(d, b, m, "baseline")
        if raw is None:
            continue
        base = {i: float(r["em"]) for i, r in raw.items()}
        b_acc = 100 * sum(base.values()) / len(base)
        cells = {}
        for col, c in COLS.items():
            raw = load(d, b, m, c)
            if raw is None:
                continue
            rec = {i: float(r["em"]) for i, r in raw.items()}
            assert set(rec) == set(base), (b, m, c, len(rec), len(base))
            a = 100 * sum(rec.values()) / len(rec)
            cells[col] = {"acc": a, "n": len(rec), "d": a - b_acc,
                          "p": None if c == "baseline" else mcnemar(base, rec),
                          "letters": letters(raw) if kind == "freeform" else 0}
        rows.append({"bench": lab, "model": mlab, "kind": kind, "cells": cells})
print(json.dumps(rows, indent=1))
