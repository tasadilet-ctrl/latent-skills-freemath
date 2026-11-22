"""Rebuild Adil's LiveMath "option 1" split (origin/adil skill_search/skillopt_local/make_split_other.py) on this box.

    python3 make_lm_split.py <work dir>
        -> <work>/lm_split_other/{train,val,test}/items.json   (SkillOpt livemathematicianbench item format)
        -> ./lm_ids_trainval.json                               (the 100 train+val ids; leave them out when scoring)

His inputs, re-derived: the kit's 608 questions = ~/for Adilet/data/livemath.jsonl; SkillOpt's original 52
train+val ids = the 608 minus ~/mcq_math/data/livemath556.jsonl; META = questions with the "stronger result can be
proven" option (his assert uses the same phrase). Pool = 608 - 52 - META = 324 OTHER questions (his docstring: 324),
ordered by sha256 of the id; train = first 60, val = next 40, test = the rest (eval_test is off).
"""
import ast
import hashlib
import json
import os
import sys

L = "ABCDEFGHIJ"
H = os.path.expanduser("~")
work = os.path.abspath(sys.argv[1])
rows = {r["id"]: r for r in map(json.loads, open(f"{H}/for Adilet/data/livemath.jsonl"))}
k556 = {json.loads(l)["id"] for l in open(f"{H}/mcq_math/data/livemath556.jsonl")}
assert k556 <= set(rows)
tv = set(rows) - k556
meta = {i for i, r in rows.items() if "stronger result can be proven" in json.dumps(r)}
assert len(rows) == 608 and len(tv) == 52, (len(rows), len(tv))


def _types(s):
    try:
        v = ast.literal_eval(s)
    except (ValueError, SyntaxError):
        v = [s]
    return v if isinstance(v, list) else [str(v)]


def item(r):  # identical to Adil's
    _, month, no = r["id"].split("-")
    opts = r["options"] if isinstance(r["options"], list) else ast.literal_eval(r["options"])
    tt = r.get("theorem_type") or "[]"
    choices = [{"label": L[i], "text": t} for i, t in enumerate(opts)]
    return {"id": f"{month}:{no}", "month": month, "no": no, "paper_link": r.get("paper_link", ""),
            "theorem": "", "sketch": "", "theorem_type": tt if isinstance(tt, list) else _types(tt),
            "question": r["question"], "choices": choices, "correct_choice": choices[L.index(r["answer"])],
            "source_path": "data/livemath.jsonl"}


pool = sorted((i for i in rows if i not in tv and i not in meta), key=lambda i: hashlib.sha256(i.encode()).hexdigest())
assert len(pool) == 324, len(pool)
split = {"train": pool[:60], "val": pool[60:100], "test": pool[100:]}
for name, ids in split.items():
    out = os.path.join(work, "lm_split_other", name)
    os.makedirs(out, exist_ok=True)
    json.dump([item(rows[i]) for i in ids], open(os.path.join(out, "items.json"), "w"), ensure_ascii=False, indent=2)
    print(name, len(ids))
json.dump(sorted(pool[:100]), open("lm_ids_trainval.json", "w"), indent=0)
print("pool", len(pool), "meta", len(meta))
