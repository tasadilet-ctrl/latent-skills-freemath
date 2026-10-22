"""MCQ math sets with no answer-format shortcut, for the text-skill comparison.

    python prepare_mcq_math.py <out dir> <SuperGPQA parquet> <MMLU-Pro test parquet>
      -> <out>/mmlupro_math_tq_sb.jsonl     MMLU-Pro math from TheoremQA + SciBench (505)
      -> <out>/supergpqa_math_hard.jsonl    SuperGPQA Mathematics, difficulty=hard, 500 by id hash

Audit (no model; audit_mcq.py, 10 options, chance 10%):
  MMLU-Pro math     meta-options 25/1351 (3 correct), centroid 11.6%, longest 11.3%  -> clean
    TheoremQA part  centroid 11.3%, longest 7.6%;  SciBench part centroid 8.1%, longest 21.1%
  SuperGPQA math    meta-options 26/2622 (1 correct), centroid 23.6% (hard: 18.0%)  -> report split
Every row carries centroid_right (does picking the option most similar to the
others get it right), so results can be split the way PROTOCOL.md splits LiveMath.
"""
import difflib, hashlib, json, os, sys
import pyarrow.parquet as pq

L = "ABCDEFGHIJ"


def centroid(opts):
    sims = [sum(difflib.SequenceMatcher(None, a, b).ratio() for j, b in enumerate(opts) if j != i)
            for i, a in enumerate(opts)]
    return max(range(len(opts)), key=sims.__getitem__)


def write(path, rows):
    with open(path, "w") as f:
        for r in rows:
            r["centroid_right"] = centroid(r["options"]) == L.index(r["answer"])
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(path, len(rows), "centroid-right", sum(r["centroid_right"] for r in rows))


out, sg_path, mp_path = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
mp = [x for x in pq.read_table(mp_path).to_pylist()
      if x["category"] == "math" and x["src"].split("-")[0] in ("theoremQA", "scibench")]
write(os.path.join(out, "mmlupro_math_tq_sb.jsonl"),
      [{"id": f"mmlupro-{x['question_id']}", "question": x["question"], "options": list(x["options"]),
        "answer": L[x["answer_index"]], "source": x["src"]} for x in mp])
sg = [x for x in pq.read_table(sg_path).to_pylist() if x["field"] == "Mathematics" and x["difficulty"] == "hard"]
sg = sorted(sg, key=lambda x: hashlib.sha256(x["uuid"].encode()).hexdigest())[:500]
write(os.path.join(out, "supergpqa_math_hard.jsonl"),
      [{"id": f"supergpqa-{x['uuid']}", "question": x["question"], "options": list(x["options"]),
        "answer": x["answer_letter"], "source": x["subfield"]} for x in sg])
