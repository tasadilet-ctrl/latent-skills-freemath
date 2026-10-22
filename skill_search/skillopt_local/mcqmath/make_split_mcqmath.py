"""Train/val/test splits for MMLU-Pro math and SuperGPQA hard math, in the mcqmath env's item format.

    python make_split_mcqmath.py <work dir> <mmlupro_math_tq_sb.jsonl> <supergpqa_math_hard.jsonl>
      -> <work>/mq_split/<bench>/{train,val,test}/items.json
      -> ids_mcqmath.json next to this file (ids + centroid labels; commit this, not the data)

Inputs come from ../../mcq_math/prepare_mcq_math.py, which also audits the
answer-format shortcuts (no model): both sets have no meta-option that is
reliably correct; MMLU-Pro's centroid shortcut is at chance, SuperGPQA's is 1.8x
chance, so its test score is reported split by centroid_right (PROTOCOL.md).

Split decided before any run: deterministic hash of the id; train 40, val 100
(SkillOpt's gate, the "dev" of PROTOCOL.md), the rest is test and is touched once.
"""
import hashlib, json, os, sys

L = "ABCDEFGHIJ"
SIZES = (40, 100)


def to_item(r: dict) -> dict:
    choices = [{"label": L[i], "text": t} for i, t in enumerate(r["options"])]
    gold = r["answer"]
    return {"id": r["id"], "question": r["question"], "choices": choices,
            "correct_choice": {"label": gold, "text": r["options"][L.index(gold)]},
            "theorem_type": [r.get("source", "mcq")], "centroid_right": r["centroid_right"],
            "theorem": "", "sketch": "", "month": "", "no": r["id"], "paper_link": ""}


work = os.path.abspath(sys.argv[1])
manifest = {}
for path in sys.argv[2:]:
    bench = os.path.basename(path).replace(".jsonl", "")
    items = [to_item(json.loads(l)) for l in open(path)]
    order = sorted(items, key=lambda it: hashlib.sha256(it["id"].encode()).hexdigest())
    parts = {"train": order[:SIZES[0]], "val": order[SIZES[0]:sum(SIZES)], "test": order[sum(SIZES):]}
    manifest[bench] = {k: [[it["id"], it["centroid_right"]] for it in v] for k, v in parts.items()}
    for k, v in parts.items():
        d = os.path.join(work, "mq_split", bench, k)
        os.makedirs(d, exist_ok=True)
        json.dump(v, open(os.path.join(d, "items.json"), "w"), ensure_ascii=False, indent=1)
    print(bench, {k: len(v) for k, v in parts.items()},
          "test centroid-right", sum(it["centroid_right"] for it in parts["test"]))
json.dump(manifest, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ids_mcqmath.json"), "w"))
